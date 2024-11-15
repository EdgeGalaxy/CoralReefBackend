from fastapi import APIRouter

from reef.core.users import fastapi_users
from reef.schemas.users import UserRead, UserUpdate


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
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
)
