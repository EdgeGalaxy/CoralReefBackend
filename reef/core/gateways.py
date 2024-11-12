from typing import List
from datetime import datetime

from loguru import logger
from beanie import PydanticObjectId

from reef.models import (
    GatewayModel,
    CameraModel,
    DeploymentModel,
    WorkspaceModel,
    GatewayStatus
)

from reef.exceptions import (
    ObjectNotFoundError,
    AssociatedObjectExistsError
)


class GatewayCore:
    def __init__(
        self,
        gateway: GatewayModel
    ):
        self.gateway = gateway
    
    async def check_gateway(self) -> None:
        """Check if gateway valid"""
        if self.gateway.status == GatewayStatus.DELETED:
            raise ObjectNotFoundError(f'网关不存在或已被删除!')
    
    @classmethod
    async def get_gateway(cls, gateway_id: str) -> 'GatewayCore':
        """Get a gateway by ID."""
        gateway = await GatewayModel.find_one(
            GatewayModel.id == PydanticObjectId(gateway_id),
            fetch_links=True
        )
        if not gateway:
            raise ObjectNotFoundError(f'网关不存在!')
        return cls(gateway=gateway)
    
    @classmethod
    async def get_workspace_gateways(cls, workspace: WorkspaceModel) -> List[GatewayModel]:
        """Get all gateways for this workspace."""
        return await GatewayModel.find(
            GatewayModel.workspace.id == workspace.id,
            GatewayModel.status != GatewayStatus.DELETED,
            fetch_links=True
        ).sort("-created_at").to_list()

    @classmethod
    async def create_gateway(cls, gateway_data: dict, workspace: WorkspaceModel) -> 'GatewayCore':
        """Create a new gateway."""
        gateway = GatewayModel(
            **gateway_data,
            workspace=workspace,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await gateway.save()
        logger.info(f'创建网关: {gateway.id}')
        return cls(gateway=gateway)

    async def update_gateway(self, gateway_data: dict) -> None:
        """Update an existing gateway."""
        await self.check_gateway()

        for key, value in gateway_data.items():
            setattr(self.gateway, key, value)
        
        self.gateway.updated_at = datetime.now()
        await self.gateway.save()

    async def delete_gateway(self) -> None:
        """Delete a gateway and update related entities."""
        await self.check_gateway()

        # Check if gateway has any deployments
        deployments = await DeploymentModel.find(
            DeploymentModel.workspace.id == self.gateway.workspace.id,
            DeploymentModel.gateway.id == self.gateway.id
        ).to_list()
        
        if deployments:
            raise AssociatedObjectExistsError("无法删除存在服务的网关!")
            
        # Update related cameras to remove gateway reference
        cameras = CameraModel.find(
            CameraModel.workspace.id == self.gateway.workspace.id,
            CameraModel.gateway.id == self.gateway.id
        )

        logger.info(f'删除与网关 {self.gateway.id} 关联的 {await cameras.count()} 台相机 & 删除网关!')

        await cameras.delete()
        self.gateway.status = GatewayStatus.DELETED
        await self.gateway.save()

    async def get_cameras(self) -> List[CameraModel]:
        """Get all cameras for this gateway."""
        await self.check_gateway()
        return await CameraModel.find(
            CameraModel.workspace.id == self.gateway.workspace.id,
            CameraModel.gateway.id == self.gateway.id,
            fetch_links=True
        ).sort("-created_at").to_list()

    async def get_deployments(self) -> List[DeploymentModel]:
        """Get all deployments for this gateway."""
        await self.check_gateway()
        return await DeploymentModel.find(
            DeploymentModel.workspace.id == self.gateway.workspace.id,
            DeploymentModel.gateway.id == self.gateway.id,
            fetch_links=True
        ).sort("-created_at").to_list()
