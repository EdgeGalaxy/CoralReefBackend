from datetime import datetime
from enum import Enum
from pydantic import Field
from beanie import Document, Link

from .workspaces import WorkspaceModel


class GatewayStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DELETED = "deleted"


class GatewayModel(Document):
    name: str = Field(description="网关名称")
    description: str = Field(description="网关描述")
    version: str = Field(description="网关版本")
    platform: str = Field(description="网关平台")
    ip_address: str = Field(default=None, description="网关IP地址")
    mac_address: str = Field(default=None, description="网关MAC地址")
    status: GatewayStatus = Field(default=GatewayStatus.OFFLINE, description="网关状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace: Link[WorkspaceModel] = Field(description="所属工作空间")

    class Settings:
        name = "gateways" 

    def get_api_url(self) -> str:
        return f"http://localhost:8001"
