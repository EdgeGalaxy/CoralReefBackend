from typing import List, Optional
from datetime import datetime

from loguru import logger
from beanie.odm.operators.find.array import ElemMatch

from reef.models import (
    CameraModel,
    WorkspaceModel,
    GatewayModel,
    DeploymentModel
)

from reef.exceptions import (
    AssociatedObjectExistsError
)


class CameraCore:
    def __init__(
        self,
        camera: CameraModel
    ):
        self.camera = camera

    @classmethod
    async def get_workspace_cameras(cls, workspace: WorkspaceModel) -> List[CameraModel]:
        """Get all cameras for this workspace."""
        return await CameraModel.find(
            CameraModel.workspace.id == workspace.id,
            fetch_links=True
        ).sort("-created_at").to_list()
    
    @classmethod
    async def create_camera(
        cls,
        camera_data: dict,
        workspace: WorkspaceModel,
        gateway: Optional[GatewayModel] = None
    ) -> 'CameraCore':
        """Create a new camera."""
        camera = CameraModel(
            **camera_data,
            workspace=workspace,
            gateway=gateway,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await camera.insert()
        logger.info(f'Created camera: {camera.id}')
        return cls(camera=camera)

    async def update_camera(self, camera_data: dict) -> None:
        """Update an existing camera."""
        for key, value in camera_data.items():
            setattr(self.camera, key, value)
        
        self.camera.updated_at = datetime.now()
        await self.camera.save()

    async def delete_camera(self) -> None:
        """Delete a camera and update related entities."""
        # Check if camera has any deployments
        deployments = await DeploymentModel.find(
            DeploymentModel.workspace.id == self.camera.workspace.id,
            ElemMatch(DeploymentModel.cameras, {"$eq": self.camera})
        ).to_list()
        
        if deployments:
            raise AssociatedObjectExistsError(
                "无法删除存在部署服务的相机!"
            )
        
        await self.camera.delete()
        logger.info(f'删除相机: {self.camera.id}')
    
    async def fetch_snapshot(self) -> None:
        """Fetch a snapshot from camera."""
        return await self.camera.fetch_snapshot()

    async def get_deployments(self) -> List[DeploymentModel]:
        """Get all deployments using this camera."""
        return await DeploymentModel.find(
            DeploymentModel.workspace.id == self.camera.workspace.id,
            ElemMatch(DeploymentModel.cameras, {"$eq": self.camera}),
            fetch_links=True
        ).sort("-created_at").to_list()
