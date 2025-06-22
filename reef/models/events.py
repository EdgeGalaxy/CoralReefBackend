from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from beanie import Document, Link
from pydantic import Field

from reef.models.workspaces import WorkspaceModel
from reef.models.gateways import GatewayModel
from reef.models.deployments import DeploymentModel


class EventType(str, Enum):
    """
    事件类型枚举
    """
    # Gateway events
    GATEWAY_REGISTER = "gateway_register"
    GATEWAY_ONLINE = "gateway_online"
    GATEWAY_OFFLINE = "gateway_offline"

    # Deployment events
    DEPLOYMENT_CREATE = "deployment_create"
    DEPLOYMENT_DELETE = "deployment_delete"
    DEPLOYMENT_PAUSE = "deployment_pause"
    DEPLOYMENT_RESUME = "deployment_resume"
    DEPLOYMENT_RESTART = "deployment_restart"


class EventModel(Document):
    """
    通用事件模型
    """
    event_type: EventType
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    # Associated objects
    workspace: Link[WorkspaceModel]
    gateway: Optional[Link[GatewayModel]] = None
    deployment: Optional[Link[DeploymentModel]] = None

    class Settings:
        name = "events"
