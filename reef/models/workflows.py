from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import Field
from beanie import Document, Link
from .workspaces import WorkspaceModel
from .users import UserModel



class WorkflowModel(Document):
    name: str = Field(description="工作流名称")
    description: str = Field(description="工作流描述")
    roboflow_id: Optional[str] = Field(default=None, description="Roboflow ID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="工作流数据")
    specification: Dict[str, Any] = Field(description="工作流定义")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace: Link[WorkspaceModel] = Field(description="所属工作空间")
    creator: Link[UserModel] = Field(description="创建者")

    class Settings:
        name = "workflows"
