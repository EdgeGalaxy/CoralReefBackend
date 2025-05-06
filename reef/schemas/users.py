
from typing import Optional
from beanie import PydanticObjectId
from fastapi_users import schemas


class UserRead(schemas.BaseUser[PydanticObjectId]):
    username: str
    phone: Optional[str] = ''


class UserCreate(schemas.BaseUserCreate):
    username: str
    phone: Optional[str] = ''

class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = None
    phone: Optional[str] = None
