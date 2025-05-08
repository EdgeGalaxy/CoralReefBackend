from typing import List
from fastapi import APIRouter, Depends, Query

from reef.core.workflows import WorkflowCore
from reef.core.workflow_template import WorkflowTemplate
from reef.models import WorkspaceModel, WorkflowModel, UserModel
from reef.schemas import CommonResponse
from reef.schemas.workflows import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
    WorkflowRename,
)
from reef.schemas.workflow_template import TemplatePublish
from reef.exceptions import AuthenticationError
from reef.api._depends import check_user_has_workspace_permission, get_workflow, get_workspace, current_user

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
    user: UserModel = Depends(current_user)
) -> WorkflowResponse:
    workflow_core = await WorkflowCore.create_workflow(
        workflow_data=workflow_data.model_dump(exclude_none=True),
        workspace=workspace,
        creator=user
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


@router.post("/{workflow_id}/publish", response_model=CommonResponse)
async def publish_template(
    template_data: TemplatePublish,
    workflow: WorkflowModel = Depends(get_workflow),
    user: UserModel = Depends(current_user)
):
    """发布工作流为模板"""
    if workflow.creator.id != user.id:
        raise AuthenticationError("无权操作此工作流")
    
    await WorkflowTemplate.publish_template(
        workflow=workflow,
        name=template_data.name,
        description=template_data.description,
        tags=template_data.tags,
        is_public=template_data.is_public
    )
    return CommonResponse(message="模板发布成功")
