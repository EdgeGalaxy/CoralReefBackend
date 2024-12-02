from fastapi import APIRouter, Query
from typing import Optional

from reef.core.ml_models import MLModelCore
from reef.schemas.ml_models import RoboflowMLModel, RoboflowMLModel


router = APIRouter(tags=["roboflow"])


@router.get("/{endpoint_type}/{model_id}", response_model=RoboflowMLModel)
async def get_roboflow_model(
    endpoint_type: str,
    model_id: str,
    api_key: Optional[str] = Query(None, description="Roboflow API密钥"),
    nocache: Optional[str] = Query(True, description="是否缓存"),
    device: Optional[str] = Query(None, description="设备ID"),
    dynamic: Optional[str] = Query(True, description="是否动态")
) -> RoboflowMLModel:
    """
    获取Roboflow模型信息
    """
    model_core = await MLModelCore.get_model_by_id(model_id)
    model = model_core.model
    data = RoboflowMLModel(
        name=model.name,
        type=model.task_type,
        colors=model.environment.COLORS,
        modelType=model.model_type,
        classes=model.environment.CLASS_MAP,
        model=model.onnx_model_url,
        environment=model.environment_url,
        rknn_model=model.rknn_model_url,
    )
    return data
