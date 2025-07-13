from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import asyncio
import threading

import cv2
import base64
import numpy as np

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
from reef.schemas.cameras import CameraWebRTCStreamRequest


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
            DeploymentModel.cameras.id == self.camera.id
        ).to_list()
        
        if deployments:
            raise AssociatedObjectExistsError(
                "无法删除存在部署服务的相机!"
            )
        
        await self.camera.delete()
        logger.info(f'删除相机: {self.camera.id}')
    
    async def fetch_snapshot(self) -> str:
        """Fetch a snapshot from camera."""
        return await self.camera.fetch_snapshot()
    
    async def get_video_info(self) -> dict:
        """Get video information from camera."""
        return await self.camera.get_video_info()

    async def get_deployments(self) -> List[DeploymentModel]:
        """Get all deployments using this camera."""
        return await DeploymentModel.find(
            DeploymentModel.workspace.id == self.camera.workspace.id,
            DeploymentModel.cameras.id == self.camera.id,
            fetch_links=True
        ).sort("-created_at").to_list()
    
    async def fetch_webrtc_video_stream(
        self, 
        webrtc_config: dict
    ) -> Dict[str, Any]:
        """通过 pipeline 客户端创建 WebRTC 视频流"""
        result = await self.camera.fetch_webrtc_video_stream(webrtc_config=webrtc_config)
        return result

