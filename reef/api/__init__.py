from contextlib import asynccontextmanager

from loguru import logger
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, Depends, APIRouter, Request, Query, HTTPException
from pydantic import ValidationError
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from reef.models import INIT_MODELS
from reef.api.users import router as users_router
from reef.api.gateways import router as gateways_router
from reef.api.workspaces import router as workspaces_router
from reef.api.cameras import router as cameras_router
from reef.api.deployments import router as deployments_router
from reef.api.workflows import router as workflows_router
from reef.api.proxy import router as proxy_router
from reef.api.roboflow import router as roboflow_router
from reef.api.ml_models import router as ml_models_router
from reef.api.blocks import router as block_router
from reef.api.workflow_template import router as workflow_template_router

from reef.core.users import current_user
from reef.core.users import fastapi_users, auth_backend
from reef.schemas.users import UserRead, UserCreate

from reef.utlis.monitor import start_monitor

from reef.config import settings
from reef.exceptions import ModelException


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(database=client.get_default_database(), document_models=INIT_MODELS)
    await start_monitor()
    yield


app = FastAPI(
    title="Coral Reef API",
    description="Coral Reef API",
    version="0.1.0",
    lifespan=lifespan,
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


noauth_router = APIRouter()
auth_router = APIRouter(dependencies=[Depends(current_user)])

auth_router.include_router(gateways_router)
auth_router.include_router(workspaces_router)
auth_router.include_router(cameras_router)
auth_router.include_router(deployments_router)
auth_router.include_router(workflows_router)
auth_router.include_router(ml_models_router)
auth_router.include_router(block_router)
auth_router.include_router(workflow_template_router)
# 用户相关
noauth_router.include_router(users_router, prefix="/auth/users", tags=["users"])
# 认证相关
noauth_router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
noauth_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# 代理相关
noauth_router.include_router(proxy_router, tags=["proxy"])
# Roboflow相关
noauth_router.include_router(roboflow_router, tags=["roboflow"])
app.include_router(noauth_router)
app.include_router(auth_router, prefix="/api/reef")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.exception(f'http exception: {exc}')
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"message": str(exc)}
    )

@app.exception_handler(ModelException)
async def model_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception(f"General exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"message": str(exc)}
    )
