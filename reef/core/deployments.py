from typing import List, Dict, Any, Optional
from datetime import datetime

from loguru import logger

from reef.models import (
    DeploymentModel,
    GatewayModel,
    CameraModel,
    WorkflowModel,
    WorkspaceModel,
    GatewayStatus,
    OperationStatus
)
from reef.exceptions import ObjectNotFoundError, InvalidStateError


async def validate_gateway(gateway: GatewayModel) -> None:
    """Validate gateway status"""
    if gateway.status != GatewayStatus.ONLINE:
        raise InvalidStateError(f"网关不在线!")

async def validate_cameras(cameras: List[CameraModel], gateway: Optional[GatewayModel] = None) -> None:
    """Validate cameras and their relationship with gateway"""
    for camera in cameras:
        if gateway and camera.gateway and camera.gateway.id != gateway.id:
            raise InvalidStateError(f"相机不属于当前网关!")


class DeploymentCore:
    def __init__(self, deployment: DeploymentModel):
        self.deployment = deployment

    async def check_deployment(self) -> None:
        """Check if deployment exists and is valid"""
        if not self.deployment:
            raise ObjectNotFoundError("服务不存在或已被删除!")

    @classmethod
    async def get_workspace_deployments(
        cls,
        workspace: WorkspaceModel
    ) -> List[DeploymentModel]:
        """Get all deployments for a workspace"""
        return await DeploymentModel.find(
            DeploymentModel.workspace.id == workspace.id,
            fetch_links=True
        ).sort("-created_at").to_list()

    @classmethod
    async def create_deployment(
        cls,
        name: str,
        description: str,
        gateway: GatewayModel,
        cameras: List[CameraModel],
        workflow: WorkflowModel,
        parameters: Dict[str, Any],
        workspace: WorkspaceModel
    ) -> 'DeploymentCore':
        """Create a new deployment"""
        await validate_gateway(gateway)
        await validate_cameras(cameras, gateway)

        deployment = DeploymentModel(
            name=name,
            description=description,
            gateway=gateway,
            cameras=cameras,
            workflow=workflow,
            parameters=parameters,
            workspace=workspace,
            running_status=OperationStatus.PENDING
        )
        await deployment.insert()
        logger.info(f"Created deployment: {deployment.id}")
        
        return cls(deployment=deployment)

    async def update_deployment(self, update_data: Dict[str, Any] = None, cameras: Optional[List[CameraModel]] = None) -> None:
        """Update deployment details"""
        await self.check_deployment()

        if cameras:
            await validate_cameras(cameras, self.deployment.gateway)
            self.deployment.cameras = cameras

        for key, value in update_data.items():
            setattr(self.deployment, key, value)
        
        await self.deployment.save()
        logger.info(f"Updated deployment: {self.deployment.id}")

    async def delete_deployment(self) -> None:
        """Delete deployment"""
        await self.check_deployment()
        await self.deployment.delete()
        # Reset deployment object
        self.deployment = None
        logger.info("Deleted deployment")

    async def get_status(self):
        """Get deployment status"""
        await self.check_deployment()
        return await self.deployment.fetch_recent_running_status()

    async def get_results(self) -> List[Dict[str, Any]]:
        """Get deployment results"""
        await self.check_deployment()
        return await self.deployment.get_pipeline_results()

    async def pause_pipeline(self) -> bool:
        """Pause pipeline"""
        await self.check_deployment()
        return await self.deployment.pause_pipeline()

    async def resume_pipeline(self) -> bool:
        """Resume pipeline"""
        await self.check_deployment()
        return await self.deployment.resume_pipeline()
