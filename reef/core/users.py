from datetime import datetime
from typing import Optional

from loguru import logger
from beanie import PydanticObjectId
from fastapi import Depends, Request, Response
from fastapi_users import BaseUserManager, FastAPIUsers, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import BeanieUserDatabase, ObjectIDIDMixin
from reef.models.users import UserModel, get_user_db
from reef.core.workspaces import WorkspaceCore
from reef.schemas.users import UserUpdate, UserCreate

SECRET = "SECRET"


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    return JWTStrategy(secret=SECRET, lifetime_seconds=36000)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


class UserManager(ObjectIDIDMixin, BaseUserManager[UserModel, PydanticObjectId]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: UserModel, request: Optional[Request] = None):
        await WorkspaceCore.create_workspace(user, {"name": "空间一", "description": "默认空间"})
        logger.info(f"用户 {user.id} 注册成功, 并创建默认空间")

    async def on_after_forgot_password(
        self, user: UserModel, token: str, request: Optional[Request] = None
    ):
        logger.info(f"用户 {user.id} 忘记密码, 重置 token: {token}")

    async def on_after_request_verify(
        self, user: UserModel, token: str, request: Optional[Request] = None
    ):
        logger.info(f"用户 {user.id} 请求验证, 验证 token: {token}")
    
    async def on_after_login(
        self, user: UserModel, request: Optional[Request] = None, response: Optional[Response] = None
    ):
        logger.info(f"用户 {user.id} 登录")
        # 更新最后登录时间
        user.last_login_at = datetime.now()
        await user.save()
        
    async def custom_oauth_callback(self, provider: str, account_id: str, user: UserUpdate) -> UserModel:
        """
        处理OAuth回调
        """
        # 首先尝试通过 account_id 查找用户
        existing_user = await UserModel.find_one(
            {f"oauth_accounts.{provider}.account_id": account_id}
        )
        
        if existing_user:
            # 用户已存在，返回用户
            return existing_user
        
        # 尝试通过邮箱查找用户
        if user.email:
            existing_user = await UserModel.find_one(
                {"email": user.email}
            )
            if existing_user:
                # 用户已存在但未关联OAuth账号，关联并返回
                # 添加OAuth账号信息
                if not hasattr(existing_user, "oauth_accounts"):
                    existing_user.oauth_accounts = []
                    
                existing_user.oauth_accounts.append({
                    "id": PydanticObjectId(),
                    "oauth_name": provider,
                    "account_id": account_id,
                    "account_email": user.email,
                    "access_token": "",
                    "refresh_token": "",
                })
                await existing_user.save()
                return existing_user
        
        # 创建新用户
        username = user.email.split("@")[0] if user.email else f"{provider}_{account_id}"
        user_create = UserCreate(
            email=user.email,
            username=username,
            password=username,
            is_active=True,
            is_verified=True,
        )
        new_user = await self.create(
            user_create,
            safe=True,
        )
        new_user.oauth_accounts.append({
            "id": PydanticObjectId(),
            "oauth_name": provider,
            "account_id": account_id,
            "account_email": user.email,
            "access_token": "",
            "refresh_token": "",
        })
        await new_user.save()
        logger.info(f"OAuth用户 {new_user.id} 注册成功")
        return new_user


async def get_user_manager(user_db: BeanieUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[UserModel, PydanticObjectId](get_user_manager, [auth_backend])

current_user = fastapi_users.current_user()
super_user = fastapi_users.current_user(superuser=True)
current_active_user = fastapi_users.current_user(active=True)