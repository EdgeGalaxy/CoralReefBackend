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
from httpx_oauth.clients.github import GitHubOAuth2
from reef.models.users import UserModel, get_user_db
from reef.core.workspaces import WorkspaceCore
from reef.config import settings

SECRET = "SECRET"


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    return JWTStrategy(secret=SECRET, lifetime_seconds=36000)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# GitHub OAuth 设置
github_oauth_client = GitHubOAuth2(
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
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
        
    async def oauth_callback(
        self, oauth_name: str, access_token: str, account_id: str, account_email: str, 
        expires_at: Optional[int] = None, refresh_token: Optional[str] = None,
        request: Optional[Request] = None, associate_by_email: bool = False,
        is_verified_by_default: bool = True
    ) -> UserModel:
        """
        处理OAuth回调
        """
        # 首先尝试通过 account_id 查找用户
        user = await self.user_db.collection.find_one(
            {f"oauth_accounts.{oauth_name}.account_id": account_id}
        )
        
        if user:
            # 用户已存在，返回用户
            return await self.user_db.get(user["_id"])
        
        # 尝试通过邮箱查找用户
        if account_email and associate_by_email:
            user = await self.user_db.collection.find_one(
                {"email": account_email}
            )
            if user:
                # 用户已存在但未关联OAuth账号，关联并返回
                user_obj = await self.user_db.get(user["_id"])
                # 添加OAuth账号信息
                if not hasattr(user_obj, "oauth_accounts"):
                    user_obj.oauth_accounts = []
                    
                user_obj.oauth_accounts.append({
                    "provider": oauth_name,
                    "account_id": account_id,
                    "account_email": account_email,
                })
                await user_obj.save()
                return user_obj
        
        # 创建新用户
        username = account_email.split("@")[0] if account_email else f"github_{account_id}"
        new_user = await self.create(
            {
                "email": account_email,
                "username": username,
                "is_active": True,
                "is_verified": is_verified_by_default,  # OAuth用户自动验证
                "oauth_accounts": [{
                    "provider": oauth_name,
                    "account_id": account_id,
                    "account_email": account_email,
                }]
            }
        )
        
        # 为新用户创建默认工作空间
        await WorkspaceCore.create_workspace(new_user, {"name": "空间一", "description": "默认空间"})
        logger.info(f"OAuth用户 {new_user.id} 注册成功, 并创建默认空间")
        
        return new_user


async def get_user_manager(user_db: BeanieUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[UserModel, PydanticObjectId](get_user_manager, [auth_backend])

current_user = fastapi_users.current_user()
super_user = fastapi_users.current_user(superuser=True)
current_active_user = fastapi_users.current_user(active=True)