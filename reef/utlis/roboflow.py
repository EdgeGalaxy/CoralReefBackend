import uuid
import platform
import json
from pathlib import Path
from typing import List, Dict

import requests
from asyncer import asyncify
from inference_sdk.http.utils.aliases import resolve_roboflow_model_alias, REGISTERED_ALIASES

from reef.config import settings
from reef.exceptions import RemoteCallError
from reef.utlis.cache import url_cache
from reef.utlis._utils import _add_params_to_url
from reef.utlis.cloud import backup_remote_url


async def get_roboflow_worflows(workflow_id: str, project_id: str = None, api_key: str = None) -> List[Dict]:
    roboflow_url = settings.roboflow_api_url
    project_id = project_id or settings.roboflow_project_id
    roboflow_api_key = api_key or settings.roboflow_api_key
    response = await asyncify(requests.get)(f"{roboflow_url}/{project_id}/workflows/{workflow_id}?api_key={roboflow_api_key}")
    return response.json()['workflow']


async def get_roboflow_model_data(model_id: str, endpoint_type: str = None, device_id: str = None, api_key: str = None) -> dict:
    roboflow_url = settings.roboflow_api_url
    roboflow_api_key = api_key or settings.roboflow_api_key
    device_id = device_id or str(uuid.uuid4())
    endpoint_type = endpoint_type or settings.get("endpoint_type", "ort")
    model_alias = resolve_roboflow_model_alias(model_id)
    if not roboflow_url or not roboflow_api_key:
        raise RemoteCallError("未配置Roboflow信息")
    params = [
        ("nocache", "true"),
        ("device", platform.node()),
        ("dynamic", "true"),
    ]
    if api_key:
        params.append(("api_key", api_key))
    try:
        api_url = _add_params_to_url(f"{roboflow_url}/{endpoint_type}/{model_alias}", params)
        response = await asyncify(requests.get)(api_url)
        if response.status_code != 200:
            raise RemoteCallError(f"Roboflow API返回错误: {response.status_code} {response.text}")
        api_data = response.json()
        if "ort" not in api_data.keys():
            raise RemoteCallError("Roboflow 错误的返回参数, 缺少 ort")
        api_data = api_data["ort"]
        if "model" not in api_data:
            raise RemoteCallError("Roboflow 错误的返回参数, 缺少 model")
        if "environment" not in api_data:
            raise RemoteCallError("Roboflow 错误的返回参数, 缺少 environment")
        environment = await asyncify(requests.get)(api_data["environment"])
    except Exception as e:
        raise RemoteCallError(f"Roboflow API返回错误: {e}")
    else:
        api_data["environment_key"] = await backup_remote_url(key=f"{model_alias}/environment.json", url=api_data["environment"])
        api_data["environment"] = environment.json()
        api_data["model"] = await backup_remote_url(key=f"{model_alias}/weights.onnx", url=api_data["model"])
    return api_data


async def get_roboflow_model_ids() -> List[str]:
    return list(REGISTERED_ALIASES.keys())


async def get_models_type() -> List[str]:
    return sorted(list(set([model_id.split("-")[0] for model_id in list(REGISTERED_ALIASES.keys())])))


async def get_base_blocks_describe() -> Dict:
    """获取区块描述信息，包含翻译后的 schema"""
    expires = 3600 * 24 * 30
    # 读取 describe.json 文件
    data = url_cache.get("base_blocks_describe", expires)
    if not data:
        describe_json_path = Path(__file__).parent.parent / 'statics' / 'describe.json'
        with open(describe_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        url_cache.set("base_blocks_describe", expires, data)
    return data


async def get_block_by_identifier(identifier: str) -> Dict:
    data = await get_base_blocks_describe()
    for block in data['blocks']:
        if block['manifest_type_identifier'] == identifier:
            return block
    return None
