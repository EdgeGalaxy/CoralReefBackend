from fastapi import APIRouter, Depends
from fastapi_users.authentication import AuthenticationBackend

from reef.core.users import fastapi_users, auth_backend, get_user_manager, UserManager
from reef.schemas.users import UserRead, UserUpdate, UserCreate
from reef.models.users import UserModel

router = APIRouter()

# 用户相关
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
)

router.include_router(
    fastapi_users.get_reset_password_router(),
)
router.include_router(
    fastapi_users.get_verify_router(UserRead),
)


@router.post("/oauth/{provider}/callback/{account_id}")
async def oauth_custom_callback(
    provider: str, 
    account_id: str,
    user: UserUpdate, 
    manager: UserManager = Depends(get_user_manager),
):
    user = await manager.custom_oauth_callback(provider, account_id, user)
    response = await auth_backend.login(auth_backend.get_strategy(), user)
    await manager.on_after_login(user)
    return response

@router.get("/check-password-reset/{account_id}")
async def check_password_reset(
    account_id: str,
    user: UserModel = Depends(fastapi_users.current_user()),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    检查用户是否需要重设密码
    条件：
    1. 检查用户的 oauth_accounts 中是否存在对应的 account_id
    2. 如果存在，检查密码是否为默认密码（等于用户名）
    """
    # 首先检查是否存在对应的 OAuth 账号
    if not user.oauth_accounts:
        return {"need_reset": False}
        
    oauth_account = next(
        (acc for acc in user.oauth_accounts if acc.account_id == account_id),
        None
    )
    
    if not oauth_account:
        return {"need_reset": False}
        
    try:
        # 使用用户名作为密码尝试验证
        is_valid = user_manager.password_helper.password_hash.verify(user.username, user.hashed_password)
        # 如果验证成功，说明密码仍然是用户名，需要重设
        return {"need_reset": is_valid}
    except Exception as e:
        print('验证过程出错', e)
        # 如果验证过程出错，返回不需要重设
        return {"need_reset": False}
