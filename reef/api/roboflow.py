from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from reef.core.ml_models import MLModelCore
from reef.schemas.ml_models import RoboflowMLModel, RoboflowMLModelResponse
from reef.utlis.cloud import sign_url


router = APIRouter(tags=["roboflow"])


@router.get("/getWeights")
async def get_weights(
    model_id: str,
    api_key: Optional[str] = Query(None, description="Roboflow API密钥"),
    nocache: Optional[str] = Query(True, description="是否缓存"),
    device: Optional[str] = Query(None, description="设备ID"),
    dynamic: Optional[str] = Query(True, description="是否动态")
) -> RoboflowMLModel:
    """
    获取Roboflow模型权重
    """
    model_core = await MLModelCore.get_model_by_id(model_id)
    return {"taskType": model_core.model.task_type}


@router.get("/ort/{model_id}", response_model=RoboflowMLModel)
async def get_roboflow_model(
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
        model=await sign_url(model.onnx_model_url),
        environment=await sign_url(model.environment_url),
        rknn_model=await sign_url(model.rknn_model_url),
    )
    return data


@router.get("/ort/{dateset_type}/{version}", response_model=RoboflowMLModelResponse)
async def get_roboflow_model_by_dateset_type_and_version(
    dateset_type: str,
    version: str,
    api_key: Optional[str] = Query(None, description="Roboflow API密钥"),
    nocache: Optional[str] = Query(True, description="是否缓存"),
    device: Optional[str] = Query(None, description="设备ID"),
    dynamic: Optional[str] = Query(True, description="是否动态")
) -> RoboflowMLModel:
    """
    获取Roboflow模型信息
    """
    model_core = await MLModelCore.get_model_by_model_alias(f'{dateset_type}/{version}')
    model = model_core.model
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    data = RoboflowMLModel(
        name=model.name,
        type=model.task_type,
        colors=model.environment.COLORS,
        modelType=model.model_type,
        classes=model.environment.CLASS_MAP,
        model=await sign_url(model.onnx_model_url),
        environment=await sign_url(model.environment_url),
        rknn_model=await sign_url(model.rknn_model_url),
    )
    response = RoboflowMLModelResponse(
        ort=data
    )
    return response