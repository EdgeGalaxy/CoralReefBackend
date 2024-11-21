from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import Field, BaseModel
from beanie import Document, Link
from .workspaces import WorkspaceModel

class MLPlatform(str, Enum):
    ROBOFLOW = "roboflow"
    CUSTOM = "custom"

class MLTaskType(str, Enum):
    OBJECT_DETECTION = "object_detection"
    CLASSIFICATION = "classification"
    SEGMENTATION = "segmentation"
    KEYPOINT = "keypoint"

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

class MLModelModel(Document):
    name: str = Field(description="模型名称")
    description: Optional[str] = Field(default=None, description="模型描述")
    platform: MLPlatform = Field(description="模型来源平台")
    dataset_url: Optional[str] = Field(default=None, description="数据集地址")
    preprocessing_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "auto-orient": {"enabled": True},
            "resize": {
                "format": "Fit (black edges) in",
                "width": 640,
                "height": 640,
                "enabled": True
            }
        },
        description="预处理配置参数"
    )
    class_mapping: Dict[str, int] = Field(description="类别和索引的映射关系")
    class_colors: Optional[Dict[str, str]] = Field(
        default=None, 
        description="类别对应的颜色(十六进制颜色代码)"
    )
    task_type: MLTaskType = Field(description="模型任务类型")
    version: str = Field(description="模型版本")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace: Link[WorkspaceModel] = Field(description="所属工作空间")

    class Settings:
        name = "ml_models"
        indexes = [
            "name",
            "platform",
            "task_type"
        ]
