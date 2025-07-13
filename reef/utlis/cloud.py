from typing import Union

import oss2
import requests
from asyncer import asyncify

from reef.config import settings
from reef.utlis.cache import url_cache
from reef.exceptions import RemoteCallError


def get_bucket():
    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)
    return bucket


def sign_url_sync(key: str, expires: int = 3600) -> str:
    if not key:
        return None
    bucket = get_bucket()
    signed_url = bucket.sign_url('GET', key, expires=expires)
    return signed_url


async def sign_url(key: str, expires: int = 3600) -> str:
    if not key:
        return None
    # Try to get from cache first
    cache_expires = expires - 60
    cached_url = url_cache.get(key, cache_expires)
    if cached_url:
        return cached_url
    # Generate new signed URL if not in cache
    bucket = get_bucket()
    signed_url = await asyncify(bucket.sign_url)('GET', key, expires=expires)
    
    # Cache the result
    url_cache.set(key, cache_expires, signed_url)
    
    return signed_url


async def backup_remote_url(key: str, url: str) -> str:
    response = await asyncify(requests.get)(url, timeout=60)
    if response.status_code != 200:
        raise RemoteCallError(f"Roboflow API返回错误: {response.status_code} {response.text}")
    bucket = get_bucket()
    await asyncify(bucket.put_object)(key=key, data=response.content)
    return key


async def upload_data_to_cloud(data: Union[str, bytes], key: str) -> str:
    bucket = get_bucket()
    await asyncify(bucket.put_object)(key=key, data=data)
    return key


async def transfer_object(source_key: str, target_key: str) -> None:
    bucket = get_bucket()
    if bucket.object_exists(source_key):
        result = await asyncify(bucket.copy_object)(source_bucket_name=settings.oss_bucket_name, source_key=source_key, target_key=target_key)
        if result.status != 200:
            raise RemoteCallError(f"上传对象失败: {result.status} {result.request_id}")
        await asyncify(bucket.delete_object)(source_key)
    elif source_key.startswith("http"):
        await backup_remote_url(target_key, source_key)
    else:
        raise RemoteCallError(f"源对象不存在: {source_key}")


async def download_from_cloud(key: str) -> bytes:
    """从OSS下载文件内容

    Args:
        key (str): OSS中的文件键值

    Raises:
        RemoteCallError: 当文件不存在或下载失败时抛出

    Returns:
        bytes: 文件内容
    """
    bucket = get_bucket()
    
    # 检查文件是否存在
    if not await asyncify(bucket.object_exists)(key):
        raise RemoteCallError(f"文件不存在: {key}")
    
    try:
        # 获取文件对象
        result = await asyncify(bucket.get_object)(key)
        # 读取所有内容
        content = result.read()
        return content
    except Exception as e:
        raise RemoteCallError(f"下载文件失败: {key}, 错误: {str(e)}")
    finally:
        if 'result' in locals():
            result.close()
