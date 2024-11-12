import asyncio
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import Field
from beanie import Document, Link, before_event, Replace, Insert, Delete

from loguru import logger
from reef.utlis.pipeline import PipelineClient

from .workspaces import WorkspaceModel
from .gateways import GatewayModel
from .cameras import CameraModel
from .workflows import WorkflowModel


class OperationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    STOPPED = "stopped"



class DeploymentModel(Document):
    name: str = Field(description="部署名称")
    description: str = Field(description="部署描述")
    gateway: Link[GatewayModel] = Field(description="网关")
    cameras: List[Link[CameraModel]] = Field(description="摄像头")
    workflow: Link[WorkflowModel] = Field(description="工作流")
    pipeline_id: Optional[str] = Field(default=None, description="pipeline id")
    running_status: OperationStatus = Field(default=OperationStatus.FAILURE, description="运行状态")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="部署参数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace: Link[WorkspaceModel] = Field(description="所属工作空间")

    class Settings:
        name = "deployments"


    @before_event([Insert])
    async def create_remote_pipeline(self):
        """Create inference pipeline before deployment is created"""
        try:
            pipeline_client = PipelineClient(self.gateway.get_api_url())
            self.pipeline_id = await pipeline_client.create_pipeline(
                video_reference=[camera.path for camera in self.cameras],
                workflow_spec=self.workflow.specification,
                workspace_name=self.workspace.name
            )
            self.running_status = OperationStatus.PENDING
            # fetch running status after 5 seconds
            loop = asyncio.get_running_loop()
            loop.call_later(5, self.fetch_recent_running_status)
            logger.info(f"Created pipeline {self.pipeline_id} for deployment")
        except Exception as e:
            logger.error(f"Failed to create pipeline: {e}")
            raise

    @before_event([Replace])
    async def handle_pipeline_update(self, old_document: "DeploymentModel"):
        """Handle pipeline updates when deployment is updated"""
        try:
            pipeline_client = PipelineClient(self.gateway.get_api_url())
            
            needs_restart = (
                self.cameras != old_document.cameras or
                self.workflow != old_document.workflow or
                self.gateway != old_document.gateway or
                self.parameters != old_document.parameters
            )
            
            if needs_restart:
                if old_document.pipeline_id:
                    await pipeline_client.terminate_pipeline(old_document.pipeline_id)
                
                self.pipeline_id = await pipeline_client.create_pipeline(
                    video_reference=[camera.path for camera in self.cameras],
                    workflow_spec=self.workflow.specification,
                    workspace_name=self.workspace.name
                )
                logger.info(f"Restarted pipeline for deployment: old={old_document.pipeline_id}, new={self.pipeline_id}")

        except Exception as e:
            logger.error(f"Failed to update pipeline: {e}")
            raise

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
            raise

    @before_event([Replace, Insert])
    def update_timestamp(self):
        """Update timestamps before save"""
        self.updated_at = datetime.now()
        if not self.created_at:
            self.created_at = datetime.now()

    async def fetch_recent_running_status(self) -> OperationStatus:
        """Fetch recent status from inference service"""
        from .metrics import PipelineMetricTimeSeries

        try:
            pipeline_client = PipelineClient(self.gateway.get_api_url())
            metrics = await pipeline_client.get_pipeline_metrics(self.pipeline_id)
            status = metrics['status']
            report = metrics['report']
            
            self.running_status = (
                OperationStatus.RUNNING if status == "success"
                else OperationStatus.STOPPED if status == "stopped"
                else OperationStatus.FAILURE
            )
            # async register metrics
            asyncio.create_task(PipelineMetricTimeSeries.register_metrics(self, report))
            await self.save()

            return self.running_status
        except Exception as e:
            logger.error(f"Failed to update deployment status: {e}")
            raise

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
            raise


