
import oss2

from reef.config import settings


def get_bucket():
    print(settings.oss_access_key_id, settings.oss_access_key_secret, settings.oss_endpoint, settings.oss_bucket_name)
    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)
    return bucket