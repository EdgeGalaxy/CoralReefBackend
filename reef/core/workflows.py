import json
import copy
from typing import List
from datetime import datetime
from loguru import logger

from reef.models import WorkflowModel, WorkspaceModel, UserModel, DeploymentModel
from reef.exceptions import ObjectNotFoundError, AssociatedObjectExistsError

class WorkflowCore:
    def __init__(
        self,
        workflow: WorkflowModel
    ):
        self.workflow = workflow
    
    @classmethod
    async def get_workflow(cls, workflow_id: str) -> 'WorkflowCore':
        """Get a workflow by ID."""
        workflow = await WorkflowModel.get(workflow_id, fetch_links=True)
        if not workflow:
            raise ObjectNotFoundError('工作流不存在!')
        return cls(workflow=workflow)
    
    @classmethod
    async def get_workspace_workflows(cls, workspace: WorkspaceModel) -> List[WorkflowModel]:
        """Get all workflows for this workspace."""
        return await WorkflowModel.find(
            WorkflowModel.workspace.id == workspace.id,
            fetch_links=True
        ).sort("-created_at").to_list()

    @classmethod
    async def create_workflow(cls, workflow_data: dict, workspace: WorkspaceModel, creator: UserModel) -> 'WorkflowCore':
        """Create a new workflow."""
        workflow = WorkflowModel(
            **workflow_data,
            workspace=workspace,
            creator=creator,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await workflow.save()
        logger.info(f'创建工作流: {workflow.id}')
        return cls(workflow=workflow)

    async def update_workflow(self, workflow_data: dict) -> None:
        """Update an existing workflow."""
        for key, value in workflow_data.items():
            setattr(self.workflow, key, value)
        
        self.workflow.updated_at = datetime.now()
        await self.workflow.save()

    async def delete_workflow(self) -> None:
        """Delete a workflow."""
        deployments_count = await DeploymentModel.find(DeploymentModel.workflow.id == self.workflow.id).count()
        if deployments_count > 0:
            raise AssociatedObjectExistsError("工作流有关联的部署, 不能删除")

        await self.workflow.delete()
        logger.info(f'删除工作流: {self.workflow.id}')
