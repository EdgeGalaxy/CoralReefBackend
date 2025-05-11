from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from reef.models.workspaces import WorkspaceModel
from reef.core.workflow_template import WorkflowTemplate
from reef.schemas import CommonResponse, PaginationResponse, PaginationParams
from reef.schemas.workflow_template import (
    TemplateResponse
)
from reef.schemas.workflow_template import WorkflowSync
from reef.models import UserModel, WorkflowTemplateModel
from reef.api._depends import current_user, get_template, get_template_with_user_check, get_workspace
from reef.exceptions import AuthenticationError

router = APIRouter(prefix="/workflows/templates", tags=["工作流模板"])

@router.post("/sync", response_model=CommonResponse)
async def sync_template(
    sync_data: WorkflowSync,
    user: UserModel = Depends(current_user)
):
    """从 Roboflow 同步工作流为模板"""
    await WorkflowTemplate.sync_from_roboflow(
        workflow_id=sync_data.workflow_id,
        creator=user,
        project_id=sync_data.project_id,
        api_key=sync_data.api_key
    )
    return CommonResponse(message="模板同步成功")

@router.get("/", response_model=PaginationResponse[TemplateResponse])
async def list_templates(
    is_public: Optional[bool] = Query(None, description="是否公开"),
    page: Optional[int] = Query(None, ge=1, description="页码"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="每页数量"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_desc: bool = Query(True, description="是否降序排序"),
    user: UserModel = Depends(current_user)
):
    """获取模板列表"""
    pagination = PaginationParams(page=page, page_size=page_size) if page and page_size else None
    return await WorkflowTemplate.list_templates(
        is_public=is_public,
        creator=user,
        pagination=pagination,
        sort_by=sort_by,
        sort_desc=sort_desc
    )

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template_detail(
    template: WorkflowTemplateModel = Depends(get_template_with_user_check),
):
    """获取模板详情"""
    if not template.is_public:
        raise AuthenticationError("无权访问此模板")
    return TemplateResponse.db_to_schema(template)

@router.post("/{template_id}/toggle-visibility", response_model=TemplateResponse)
async def toggle_template_visibility(
    template: WorkflowTemplateModel = Depends(get_template_with_user_check),
):
    """切换模板可见性"""
    template_core = WorkflowTemplate(template=template)
    await template_core.toggle_visibility()
    return TemplateResponse.db_to_schema(template)

@router.post("/{template_id}/fork/{workspace_id}", response_model=CommonResponse)
async def fork_template(
    workspace: WorkspaceModel = Depends(get_workspace),
    template: WorkflowTemplateModel = Depends(get_template),
):
    """复制模板到工作空间"""
    if not template.is_public:
        raise AuthenticationError("无权访问此模板")
    
    template_core = WorkflowTemplate(template=template)
    await template_core.fork_to_workspace(workspace)
    return CommonResponse(message="模板复制成功")

@router.delete("/{template_id}", response_model=CommonResponse)
async def delete_template(
    template: WorkflowTemplateModel = Depends(get_template_with_user_check),
):
    """删除模板"""
    
    template_core = WorkflowTemplate(template=template)
    await template_core.delete_template()
    return CommonResponse(message="模板删除成功") 