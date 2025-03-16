import json
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, Field, model_validator


from reef.models.ml_models import (
    MLPlatform,
    MLTaskType,
    DatasetType,
    PreprocessingConfig,
    MLModelModel
)
from reef.utlis._utils import class_colors_to_hex
from reef.utlis.cloud import sign_url



class RoboflowMLModel(BaseModel):
    name: str = Field(description="模型名称")
    type: str = Field(description="模型类型")
    icon: Optional[str] = Field(default=None, description="模型图标")
    iconHasAnnotation: Optional[bool] = Field(default=None, description="模型图标是否包含注释")
    annotation: Optional[str] = Field(default=None, description="模型注释")
    colors: Optional[Dict[str, str]] = Field(default=None, description="类别对应的颜色(十六进制颜色代码)")
    modelType: str = Field(description="模型任务类型")
    classes: Dict[str, str] = Field(default=None, description="类别信息")
    model: str = Field(description="模型地址")
    environment: str = Field(description="环境信息地址")
    rknn_model: Optional[str] = Field(default=None, description="RKNN模型地址")


class RoboflowMLModelResponse(BaseModel):
    ort: RoboflowMLModel = Field(description="ONNX模型信息")
    

class MLModelBase(BaseModel):
    description: Optional[str] = Field(default=None, description="模型描述")
    platform: MLPlatform = Field(description="模型来源平台")
    dataset_url: Optional[str] = Field(default=None, description="数据集地址")
    dataset_type: DatasetType = Field(description="数据集类型")
    preprocessing_config: PreprocessingConfig = Field(description="预处理配置参数")
    class_mapping: Dict[str, str] = Field(description="类别和索引的映射关系")
    class_colors: Optional[Dict[str, str]] = Field(
        default=None,
        description="类别对应的颜色(十六进制颜色代码)"
    )
    task_type: MLTaskType = Field(description="模型任务类型")
    model_type: str = Field(description="模型类型")
    onnx_model_url: str = Field(description="ONNX模型地址")
    rknn_model_url: Optional[str] = Field(default=None, description="RKNN模型地址")
    is_public: bool = Field(default=False, description="是否公开")

    @model_validator(mode='before')
    def generate_class_colors(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get('class_colors') and values.get('class_mapping'):
            values['class_colors'] = class_colors_to_hex(values['class_mapping'])
        return values


class MLModelCreate(MLModelBase):
    batch_size: int = Field(default=8, description="批处理大小")
    workspace_id: str = Field(description="所属工作空间ID")

    @property
    def name(self) -> str:
        width = self.preprocessing_config.resize.width
        height = self.preprocessing_config.resize.height
        if width == height:
            return f"{self.model_type}-{width}"
        return f"{self.model_type}-{width}x{height}"
    

class MLModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class MLModelResponse(MLModelBase):
    id: str
    name: str
    version: str
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    async def db_to_schema(cls, db: MLModelModel) -> Optional["MLModelResponse"]:
        """Factory method to create response from database model."""
        onnx_model_url = await sign_url(db.onnx_model_url) if db.onnx_model_url else ''
        rknn_model_url = await sign_url(db.rknn_model_url) if db.rknn_model_url else ''
        
        return cls(
            id=str(db.id),
            name=db.name,
            description=db.description,
            platform=db.platform,
            dataset_url=db.dataset_url,
            dataset_type=db.dataset_type,
            preprocessing_config=json.loads(db.environment.PREPROCESSING),
            class_mapping=db.environment.CLASS_MAP,
            class_colors=db.environment.COLORS,
            task_type=db.task_type,
            model_type=db.model_type,
            onnx_model_url=onnx_model_url,
            rknn_model_url=rknn_model_url,
            version=db.version,
            is_public=db.is_public,
            workspace_id=str(db.workspace.id) if db.workspace else '',
            workspace_name=db.workspace.name if db.workspace else '',
            created_at=db.created_at,
            updated_at=db.updated_at
        )
 