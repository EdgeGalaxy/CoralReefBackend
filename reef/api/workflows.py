from typing import List
from fastapi import APIRouter, Depends

from reef.core.workflows import WorkflowCore
from reef.models import WorkspaceModel, WorkflowModel
from reef.schemas import CommonResponse
from reef.schemas.workflows import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
    WorkflowRename
)
from reef.api._depends import check_user_has_workspace_permission, get_workflow, get_workspace


router = APIRouter(
    prefix="/workspaces/{workspace_id}/workflows",
    tags=["workflows"],
    dependencies=[Depends(check_user_has_workspace_permission)]
)

@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    workspace: WorkspaceModel = Depends(get_workspace)
) -> List[WorkflowResponse]:
    workflows = await WorkflowCore.get_workspace_workflows(workspace=workspace)
    return [WorkflowResponse.db_to_schema(w) for w in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_detail(
    workflow: WorkflowModel = Depends(get_workflow)
) -> WorkflowResponse:
    return WorkflowResponse.db_to_schema(workflow)


@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    workflow_data: WorkflowCreate,
    workspace: WorkspaceModel = Depends(get_workspace),
) -> WorkflowResponse:
    workflow_core = await WorkflowCore.create_workflow(
        workflow_data=workflow_data.model_dump(exclude_none=True),
        workspace=workspace
    )
    return WorkflowResponse.db_to_schema(workflow_core.workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_data: WorkflowUpdate,
    workflow: WorkflowModel = Depends(get_workflow),
) -> WorkflowResponse:
    workflow_core = WorkflowCore(workflow=workflow)
    await workflow_core.update_workflow(workflow_data=workflow_data.model_dump(exclude_none=True))
    return WorkflowResponse.db_to_schema(workflow_core.workflow)


@router.put("/{workflow_id}/rename", response_model=WorkflowResponse)
async def rename_workflow(
    workflow_data: WorkflowRename,
    workflow: WorkflowModel = Depends(get_workflow),
) -> WorkflowResponse:
    workflow_core = WorkflowCore(workflow=workflow)
    await workflow_core.update_workflow(workflow_data=workflow_data.model_dump(exclude_none=True))
    return WorkflowResponse.db_to_schema(workflow_core.workflow)


@router.delete("/{workflow_id}", response_model=CommonResponse)
async def delete_workflow(
    workflow: WorkflowModel = Depends(get_workflow),
) -> CommonResponse:
    workflow_core = WorkflowCore(workflow=workflow)
    await workflow_core.delete_workflow()
    return CommonResponse(message="工作流删除成功")
