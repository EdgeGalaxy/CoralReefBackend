from datetime import datetime
from enum import Enum
from pydantic import Field
from beanie import Document, Link
from .users import UserModel

class WorkspaceRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"

class WorkspaceModel(Document):
    name: str = Field(description="工作空间名称")
    description: str = Field(description="工作空间描述")
    owner_user: Link[UserModel] = Field(description="工作空间所有者")
    max_users: int = Field(default=10, description="最大用户数量")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Settings:
        name = "workspaces"


class WorkspaceUserModel(Document):
    user: Link[UserModel] = Field(description="用户")
    workspace: Link[WorkspaceModel] = Field(description="工作空间")
    role: WorkspaceRole = Field(description="角色")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Settings:
        name = "workspace_users"
