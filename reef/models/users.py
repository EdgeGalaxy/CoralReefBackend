from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import Field
from beanie import Document

from fastapi_users.db import BeanieUserDatabase, BaseOAuthAccount, BeanieBaseUser



class OAuthAccountModel(BaseOAuthAccount, Document):
    pass

    class Settings:
        name = "oauth_accounts"


class UserModel(BeanieBaseUser, Document):
    username: str = Field(description="用户名", indexed=True)
    phone: Optional[str] = Field(default=None, description="手机号码", unique=True, indexed=True)

    oauth_accounts: List[OAuthAccountModel] = Field(default_factory=list, description="OAuth账户")
    
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Settings(BeanieBaseUser.Settings):
        name = "users"


async def get_user_db():
    yield BeanieUserDatabase(UserModel, OAuthAccountModel)