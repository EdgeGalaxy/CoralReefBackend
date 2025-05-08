from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import Field
from beanie import Document, Link
from .users import UserModel

class WorkflowTemplateModel(Document):
    name: str = Field(description="模板名称")
    description: str = Field(description="模板描述")
    specification: Dict[str, Any] = Field(description="工作流定义")
    data: Optional[Dict[str, Any]] = Field(default=None, description="工作流数据")
    is_public: bool = Field(default=False, description="是否公开")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    creator: Link[UserModel] = Field(description="创建者")
    usage_count: int = Field(default=0, description="使用次数")
    tags: list[str] = Field(default=[], description="标签")
    roboflow_id: Optional[str] = Field(default=None, description="Roboflow ID")

    class Settings:
        name = "workflow_templates" 