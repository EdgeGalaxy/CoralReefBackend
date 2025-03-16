from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from loguru import logger

from reef.core.ml_models import MLModelCore
from reef.models import WorkspaceModel, MLModelModel
from reef.schemas import CommonResponse
from reef.schemas.ml_models import (
    MLModelCreate,
    MLModelResponse,
    MLModelUpdate,
)
from reef.api._depends import check_user_has_workspace_permission, get_workspace, get_ml_model


router = APIRouter(
    prefix="/workspaces/{workspace_id}/models",
    tags=["ML Models"],
    dependencies=[Depends(check_user_has_workspace_permission)]
)


@router.get("/")
async def list_models(
    is_public: bool = False,
    workspace: WorkspaceModel = Depends(get_workspace)
) -> List[MLModelResponse]:
    """List all ML models in a workspace."""
    if is_public:
        models = await MLModelCore.get_public_models()
    else:
        models = await MLModelCore.get_workspace_models(workspace=workspace)
    return [await MLModelResponse.db_to_schema(m) for m in models]


@router.post("/custom", response_model=MLModelResponse)
async def create_custom_model(
    model_data: MLModelCreate,
    workspace: WorkspaceModel = Depends(get_workspace),
) -> MLModelResponse:
    """Register a custom ML model."""
    model_core = await MLModelCore.register_custom_model(
        data=model_data,
        workspace=workspace
    )
    return await MLModelResponse.db_to_schema(model_core.model)


@router.post("/public/{model_id}", response_model=MLModelResponse)
async def register_roboflow_model(
    model_id: str,
    workspace: WorkspaceModel = Depends(get_workspace),
) -> MLModelResponse:
    """Register a Roboflow model."""
    model_core = await MLModelCore.register_roboflow_model(
        model_id=model_id,
        workspace=workspace
    )
    return await MLModelResponse.db_to_schema(model_core.model)


@router.get("/public/models", response_model=List[str])
async def list_roboflow_models() -> List[str]:
    """List all Roboflow models."""
    return await MLModelCore.get_roboflow_model_ids()


@router.get("/type", response_model=List[str])
async def list_models_type() -> List[str]:
    """List all ML model types."""
    return await MLModelCore.get_models_type()


@router.get("/{model_id}", response_model=MLModelResponse)
async def get_model(
    model: MLModelModel = Depends(get_ml_model),
) -> MLModelResponse:
    """Get an ML model."""
    return await MLModelResponse.db_to_schema(model)


@router.put("/{model_id}", response_model=CommonResponse)
async def update_model(
    model_data: MLModelUpdate,
    model: MLModelModel = Depends(get_ml_model),
) -> CommonResponse:
    """Update an ML model."""
    model_core = MLModelCore(model=model)
    await model_core.update_model(model_data=model_data.model_dump(exclude_none=True))
    return CommonResponse(message="模型更新成功")


@router.delete("/{model_id}", response_model=CommonResponse)
async def delete_model(
    model: MLModelModel = Depends(get_ml_model),
) -> CommonResponse:
    """Delete an ML model."""
    model_core = MLModelCore(model=model)
    await model_core.delete_model()
    return CommonResponse(message="模型删除成功")


@router.post("/{model_id}/convert", response_model=CommonResponse)
async def convert_onnx_to_rknn(
    model: MLModelModel = Depends(get_ml_model),
) -> CommonResponse:
    """Convert ONNX model to RKNN model."""
    model_core = MLModelCore(model=model)
    await model_core.convert_onnx_to_rknn()
    return CommonResponse(message="模型转换成功")
