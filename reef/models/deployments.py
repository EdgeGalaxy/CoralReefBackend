import asyncio
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import Field
from beanie import Document, Link, before_event, Replace, Insert, Delete

from inference_sdk.http.errors import HTTPCallErrorError

import requests
from loguru import logger

from reef.utlis.pipeline import PipelineClient
from reef.utlis.cloud import sign_url
from reef.exceptions import RemoteCallError

from .workspaces import WorkspaceModel
from .gateways import GatewayModel
from .cameras import CameraModel, CameraType
from .workflows import WorkflowModel

class OperationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WARNING = "warning"
    FAILURE = "failure"
    MUTED = "muted"
    # PAUSED = "paused"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"

class DeploymentModel(Document):
    name: str = Field(description="部署名称")
    description: str = Field(description="部署描述")
    gateway: Link[GatewayModel] = Field(description="网关")
    cameras: List[Link[CameraModel]] = Field(description="摄像头")
    workflow: Link[WorkflowModel] = Field(description="工作流")
    workflow_md5: Optional[str] = Field(default=None, description="workflow specification 的 md5")
    cameras_md5: Optional[str] = Field(default=None, description="cameras 列表的 md5")
    pipeline_id: Optional[str] = Field(default=None, description="pipeline id")
    running_status: OperationStatus = Field(default=OperationStatus.PENDING, description="运行状态")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="部署参数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace: Link[WorkspaceModel] = Field(description="所属工作空间")
    class Settings:
        name = "deployments"
    
    def __replace_spec_inputs(self, spec: Dict[str, Any]):
        """Replace spec inputs with parameters"""
        for input in spec['inputs']:
            if input['type'] == 'WorkflowParameter' and input['name'] in self.parameters:
                input['default_value'] = self.parameters[input['name']]
        return spec
    
    async def _delayed_fetch_running_status(self):
        """Fetch running status after 3 seconds"""
        await asyncio.sleep(3)
        await self.fetch_recent_running_status()
    
    async def _video_file_to_signed_url(self, video_file: str) -> str:
        """Convert video file to signed url"""
        return await sign_url(video_file, expires=3600 * 24 * 30)
    
    async def _fetch_video_reference(self) -> List[str]:
        """Fetch video reference"""
        video_reference = []
        for camera in self.cameras:
            if camera.type == CameraType.FILE:
                path = await self._video_file_to_signed_url(camera.path)
            else:
                path = camera.path
            video_reference.append(path)
        return video_reference

    @before_event([Insert])
    async def create_remote_pipeline(self):
        """Create inference pipeline before deployment is created"""
        try:
            pipeline_client = PipelineClient(self.gateway.get_api_url())
            self.pipeline_id = await pipeline_client.create_pipeline(
                video_reference=await self._fetch_video_reference(),
                workflow_spec=self.__replace_spec_inputs(self.workflow.specification),
                workspace_name=self.workspace.name
            )
            self.running_status = OperationStatus.PENDING
            # fetch running status after 5 seconds
            asyncio.create_task(self._delayed_fetch_running_status())
            logger.info(f"Created pipeline {self.pipeline_id} for deployment")
        except Exception as e:
            logger.error(f"Failed to create pipeline: {e}")
            raise RemoteCallError(f"远程创建推理管道失败")

    async def handle_pipeline_update(self, old_document: "DeploymentModel"):
        """Handle pipeline updates when deployment is updated"""
        try:
            pipeline_client = PipelineClient(self.gateway.get_api_url())
            
            needs_restart = (
                [camera.id for camera in self.cameras] != [camera.id for camera in old_document.cameras] or
                self.workflow.id != old_document.workflow.id or
                self.gateway.id != old_document.gateway.id or
                self.parameters != old_document.parameters or
                self.workflow_md5 != old_document.workflow_md5 or
                self.cameras_md5 != old_document.cameras_md5
            )
            
            if needs_restart:
                if old_document.pipeline_id:
                    await pipeline_client.terminate_pipeline(old_document.pipeline_id)
                
                self.pipeline_id = await pipeline_client.create_pipeline(
                    video_reference=await self._fetch_video_reference(),
                    workflow_spec=self.__replace_spec_inputs(self.workflow.specification),
                    workspace_name=self.workspace.name
                )
                logger.info(f"Restarted pipeline for deployment: old={old_document.pipeline_id}, new={self.pipeline_id}")

        except Exception as e:
            logger.error(f"Failed to update pipeline: {e}")
            raise RemoteCallError(f"远程更新推理管道失败")

    async def trigger_update(self):
        """Trigger pipeline update manually"""
        old_document = await DeploymentModel.get(self.id, fetch_links=True)
        await self.handle_pipeline_update(old_document)
        await self.save()

    @before_event([Delete])
    async def cleanup_pipeline(self):
        """Cleanup pipeline before deployment is deleted"""
        try:
            if self.pipeline_id:
                pipeline_client = PipelineClient(self.gateway.get_api_url())
                await pipeline_client.terminate_pipeline(self.pipeline_id)
                logger.info(f"Terminated pipeline {self.pipeline_id}")
        except Exception as e:
            logger.error(f"Failed to terminate pipeline: {e}")
            raise RemoteCallError(f"远程终止推理管道失败")

    @before_event([Replace, Insert])
    def update_timestamp(self):
        """Update timestamps before save"""
        self.updated_at = datetime.now()
        if not self.created_at:
            self.created_at = datetime.now()

    async def get_status(self, status: str, report: Dict[str, Any]) -> OperationStatus:
        """Get status"""
        if status == "failure":
            running_status = OperationStatus.FAILURE
        if status == "not_found":
            running_status = OperationStatus.NOT_FOUND
        if status == "success":
            if not report:
                running_status = OperationStatus.PENDING
            sources_metadata = report['sources_metadata']

            source_status = [source_metadata['state'] for source_metadata in sources_metadata]
            if all([source_status == "RUNNING" for source_status in source_status]):
                running_status = OperationStatus.RUNNING
            # elif all([source_status == "PAUSED" for source_status in source_status]):
            #     running_status = OperationStatus.PAUSED
            elif all([source_status == "MUTED" for source_status in source_status]):
                running_status = OperationStatus.MUTED
            else:
                running_status = OperationStatus.WARNING
        return running_status

    async def fetch_recent_running_status(self) -> OperationStatus:
        """Fetch recent status from inference service"""
        from .metrics import PipelineMetricTimeSeries

        try:
            pipeline_client = PipelineClient(self.gateway.get_api_url())
            metrics = await pipeline_client.get_pipeline_metrics(self.pipeline_id)
            status = metrics['status']
            report = metrics['report']
            
            self.running_status = await self.get_status(status, report)
            # async register metrics
            asyncio.create_task(PipelineMetricTimeSeries.register_metrics(self, report))
            await self.save()

            return self.running_status
        except requests.exceptions.ConnectionError:
            self.running_status = OperationStatus.TIMEOUT
            await self.save()
            return self.running_status
        except HTTPCallErrorError as e:
            error_status = e.status_code
            self.running_status = OperationStatus.NOT_FOUND if error_status == 404 else OperationStatus.FAILURE
            await self.save()
            return self.running_status
        except Exception as e:
            logger.exception(f"Failed to update deployment status: {e}")
            raise RemoteCallError(f"远程更新部署状态失败")

    async def get_pipeline_results(self, exclude_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Get pipeline results"""
        from .metrics import PipelineResultModelTimeSeries
        try:
            pipeline_client = PipelineClient(self.gateway.get_api_url())
            results = await pipeline_client.get_pipeline_results(self.pipeline_id, exclude_fields)
            # async register results
            asyncio.create_task(PipelineResultModelTimeSeries.register_results(self, results))
            return results
        except Exception as e:
            logger.error(f"Failed to get pipeline results: {e}")
            raise RemoteCallError(f"远程获取推理管道结果失败")

    async def pause_pipeline(self) -> bool:
        """Pause pipeline"""
        pipeline_client = PipelineClient(self.gateway.get_api_url())
        success = await pipeline_client.pause_pipeline(self.pipeline_id)
        if success:
            self.running_status = OperationStatus.MUTED
            await self.save()
            return success
        raise RemoteCallError(f"远程暂停推理管道失败")

    async def resume_pipeline(self) -> bool:
        """Resume pipeline"""
        pipeline_client = PipelineClient(self.gateway.get_api_url())
        success = await pipeline_client.resume_pipeline(self.pipeline_id)
        if success:
            self.running_status = OperationStatus.RUNNING
            await self.save()
            return success
        raise RemoteCallError(f"远程恢复推理管道失败")
