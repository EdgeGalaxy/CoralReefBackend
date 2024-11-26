
from .users import UserModel, OAuthAccountModel
from .workspaces import WorkspaceModel, WorkspaceUserModel, WorkspaceRole
from .gateways import GatewayModel, GatewayStatus
from .cameras import CameraModel, CameraType
from .workflows import WorkflowModel
from .deployments import DeploymentModel, OperationStatus
from .ml_models import (
    MLModelModel, 
    MLPlatform, 
    MLTaskType,
    Environment,
    PreprocessingConfig,
    ResizeConfig,
    AutoOrientConfig
)



INIT_MODELS = [
    UserModel,
    OAuthAccountModel,
    GatewayModel,
    CameraModel,
    WorkflowModel,
    MLModelModel,
    DeploymentModel,
    WorkspaceModel,
    WorkspaceUserModel,
]

__all__ = [
    "UserModel",
    "UserStatus",
    "WorkspaceModel",
    "WorkspaceUserModel",
    "WorkspaceRole",
    "GatewayModel",
    "GatewayStatus",
    "CameraModel",
    "CameraType",
    "WorkflowModel",
    "DeploymentModel",
    "MLModelModel",
    "MLPlatform",
    "MLTaskType",
    "PreprocessingConfig",
    "ResizeConfig",
    "AutoOrientConfig",
    "OperationStatus",
    "INIT_MODELS"
]