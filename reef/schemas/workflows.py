from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field

from reef.models.workflows import WorkflowModel


class WorkflowBase(BaseModel):
    name: str = Field(description="工作流名称")
    description: str = Field(description="工作流描述")
    specification: Dict[str, Any] = Field(description="工作流定义")


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(WorkflowBase):
    name: str | None = None
    description: str | None = None
    specification: Dict[str, Any] | None = None


class WorkflowResponse(WorkflowBase):
    id: str
    created_at: datetime
    updated_at: datetime
    workspace_id: str
    workspace_name: str

    @classmethod
    def db_to_schema(cls, workflow: WorkflowModel):
        return cls(
            id=str(workflow.id),
            name=workflow.name,
            description=workflow.description,
            specification=workflow.specification,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            workspace_id=str(workflow.workspace.id),
            workspace_name=workflow.workspace.name,
        )
