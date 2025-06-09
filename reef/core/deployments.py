import asyncio
from typing import List, Dict, Any, Optional
import hashlib

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
    async def sync_status(cls, workspace: WorkspaceModel) -> None:
        """Sync deployment status"""
        deployments = await cls.get_workspace_deployments(workspace)
        await asyncio.gather(*[deployment.fetch_recent_running_status() for deployment in deployments])

    @staticmethod
    def _calc_cameras_md5(cameras: List[CameraModel]):
        """根据摄像头的 type 和 path 计算 cameras_md5"""
        md5_list = []
        for camera in cameras:
            # 支持 Link 类型和 CameraModel 实例
            cam_type = camera.type
            cam_path = camera.path
            s = f"{cam_type}:{cam_path}"
            md5_list.append(hashlib.md5(s.encode('utf-8')).hexdigest())
        # 汇总所有 camera 的 md5，再整体算 md5
        all_md5 = ''.join(sorted(md5_list))
        return hashlib.md5(all_md5.encode('utf-8')).hexdigest() if md5_list else None

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
            running_status=OperationStatus.PENDING,
            workflow_md5=workflow.specification_md5,
            cameras_md5=cls._calc_cameras_md5(cameras)
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
            # 更新 cameras_md5
            self.deployment.cameras_md5 = self._calc_cameras_md5(self.deployment.cameras)

        for key, value in update_data.items():
            setattr(self.deployment, key, value)
        
        await self.deployment.trigger_update()
        logger.info(f"Updated deployment: {self.deployment.id}")

    async def compare_config(self) -> dict:
        """
        比较当前 deployment 的 workflow_md5 和 cameras_md5 是否与最新 workflow/cameras 的 md5 一致
        """
        # 获取最新 workflow md5
        workflow_md5 = self.deployment.workflow.specification_md5
        workflow_changed = (self.deployment.workflow_md5 != workflow_md5)

        # 计算最新 cameras md5
        cameras = self.deployment.cameras
        cameras_md5 = self._calc_cameras_md5(cameras)
        cameras_changed = (self.deployment.cameras_md5 != cameras_md5)

        return {
            'workflow_changed': workflow_changed,
            'cameras_changed': cameras_changed
        }

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
    
    async def offer_pipeline(self, offer_request: Dict[str, Any]) -> bool:
        """Offer pipeline"""
        await self.check_deployment()
        return await self.deployment.offer_pipeline(offer_request)

    async def restart_pipeline(self) -> tuple[bool, str]:
        """Restart pipeline with latest configuration"""
        await self.check_deployment()
        diff_result = await self.compare_config()
        if not diff_result['workflow_changed'] and not diff_result['cameras_changed']:
            return True, "无需更新"
        
        if diff_result['workflow_changed']:
            self.deployment.parameters = {
                item['name']: self.deployment.parameters.get(item['name'], item['default_value']) 
                for item in self.deployment.workflow.specification.get('inputs', [])
                if item['type'] == 'WorkflowParameter'
            }
        
        # 更新 md5
        self.deployment.workflow_md5 = self.deployment.workflow.specification_md5
        self.deployment.cameras_md5 = self._calc_cameras_md5(self.deployment.cameras)
        
        # 手动触发更新
        await self.deployment.trigger_update()
        
        logger.info(f"Restarted pipeline for deployment: {self.deployment.id}")
        return True, "更新成功"
