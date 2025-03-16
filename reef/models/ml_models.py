from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import Field, BaseModel
from beanie import Document, Link
from .workspaces import WorkspaceModel

class MLPlatform(str, Enum):
    ROBOFLOW = "public"
    CUSTOM = "custom"

class MLTaskType(str, Enum):
    OBJECT_DETECTION = "object-detection"
    CLASSIFICATION = "classification"
    SEGMENTATION = "segmentation"
    KEYPOINT = "keypoint"


class DatasetType(str, Enum):
    COCO = "coco"
    YOLO = "yolo"


class MLModelType(str, Enum):
    YOLOV5 = "yolov5"
    YOLOV8 = "yolov8n"

    YOLOV7 = "yolov7"
    YOLOV6 = "yolov6"
    YOLOV4 = "yolov4"
    YOLOV3 = "yolov3"


class ResizeConfig(BaseModel):
    format: str = Field(default="Fit (black edges) in", description="调整大小的格式")
    width: int = Field(default=640, description="图像宽度")
    height: int = Field(default=640, description="图像高度")
    enabled: bool = Field(default=True, description="是否启用调整大小")
    
    model_config = {
        "extra": "allow"
    }

class AutoOrientConfig(BaseModel):
    enabled: bool = Field(default=True, description="是否启用自动方向")
    
    model_config = {
        "extra": "allow"
    }

class PreprocessingConfig(BaseModel):
    auto_orient: AutoOrientConfig = Field(
        default_factory=AutoOrientConfig,
        description="自动方向配置"
    )
    resize: ResizeConfig = Field(
        default_factory=ResizeConfig,
        description="调整大小配置"
    )
    additional_configs: Dict[str, Any] = Field(
        default_factory=dict,
        description="其他预处理配置"
    )
    
    model_config = {
        "extra": "allow"
    }

class Environment(BaseModel):
    PREPROCESSING: str = Field(description="预处理配置参数")
    CLASS_MAP: Dict[str, str] = Field(description="类别和索引的映射关系")
    COLORS: Optional[Dict[str, str]] = Field(
        default=None, 
        description="类别对应的颜色(十六进制颜色代码)"
    )
    BATCH_SIZE: int = Field(default=8, description="批处理大小")
    
    model_config = {
        "extra": "allow"
    }

class MLModelModel(Document):
    name: str = Field(description="模型名称", unique=True)
    description: Optional[str] = Field(default=None, description="模型描述")
    platform: MLPlatform = Field(description="模型来源平台")
    dataset_url: Optional[str] = Field(default=None, description="数据集地址")
    dataset_type: DatasetType = Field(description="数据集类型")
    task_type: MLTaskType = Field(description="模型任务类型")
    model_type: str = Field(description="模型类型")
    onnx_model_url: str = Field(description="ONNX模型地址")
    environment: Environment = Field(description="环境配置参数")
    environment_url: str = Field(description="环境配置地址")
    rknn_model_url: Optional[str] = Field(default=None, description="RKNN模型地址")
    version: str = Field(description="模型版本")
    is_public: bool = Field(default=False, description="是否公开")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace: Optional[Link[WorkspaceModel]] = Field(default=None, description="所属工作空间")

    class Settings:
        name = "ml_models"
        indexes = [
            "name",
            "platform",
            "task_type"
        ]

    @classmethod
    async def pick_new_dataset_version(cls, dataset_type: DatasetType) -> str:
        dataset_models = await cls.find(cls.dataset_type == dataset_type).sort("-created_at").to_list()
        if dataset_models:
            custom_dataset_type, index = dataset_models[0].version.split('/')
            index = int(index) + 1
        else:
            custom_dataset_type = dataset_type
            index = 1
        return f"{custom_dataset_type}/{index}"
