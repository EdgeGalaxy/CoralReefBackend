from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from reef.core.workspaces import WorkspaceCore
from reef.models import UserModel, WorkspaceModel, WorkspaceRole
from reef.core.users import current_user, super_user
from reef.schemas import CommonResponse, PaginationResponse
from reef.schemas.workspaces import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceDetailResponse,
    WorkspaceUpdate,
)
from math import ceil


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    user: UserModel = Depends(current_user)
) -> WorkspaceResponse:
    workspace_core = await WorkspaceCore.create_workspace(
        user=user,
        workspace_data=workspace_data.model_dump()
    )
    return WorkspaceResponse.db_to_schema(workspace_core.workspace)


@router.get("/{workspace_id}/users/{owner_user_id}/{role}/{invited_user_email}", response_model=CommonResponse)
async def add_workspace_user(
    workspace_id: str,
    owner_user_id: str,
    role: WorkspaceRole,
    invited_user_email: str,
    user: UserModel = Depends(current_user)
) -> CommonResponse:
    workspace = await WorkspaceModel.get(workspace_id, fetch_links=True)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作空间不存在")
    owner_user = await UserModel.get(owner_user_id)
    if not owner_user:  
        raise HTTPException(status_code=404, detail="邀请用户不存在")

    invited_user = await UserModel.find_one(UserModel.email == invited_user_email)
    if not invited_user:
        raise HTTPException(status_code=404, detail="被邀请用户不存在")

    print(f"owner_user_id: {owner_user_id}, user.id: {user.id}")
    
    if owner_user_id != str(user.id):
        raise HTTPException(status_code=400, detail="管理员用户与当前登陆用户不一致")

    if role not in WorkspaceRole:
        raise HTTPException(status_code=400, detail="角色不存在")
    
    workspace_core = WorkspaceCore(workspace=workspace)
    await workspace_core.add_user(
        owner_user=owner_user,
        invited_user=invited_user,
        role=role
    )
    return CommonResponse(message="用户已添加到工作空间")

@router.delete("/{workspace_id}/users/{user_id}")
async def remove_workspace_user(
    workspace_id: str,
    user_id: str,
    user: UserModel = Depends(current_user)
):
    workspace = await WorkspaceModel.get(workspace_id, fetch_links=True)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作空间不存在")
        
    user = await UserModel.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    workspace_core = WorkspaceCore(workspace=workspace)
    await workspace_core.remove_user(user=user)
    return CommonResponse(message="用户已从工作空间移除")


@router.get("/me", response_model=PaginationResponse[WorkspaceDetailResponse])
async def get_my_workspaces(
    current_user: UserModel = Depends(current_user),
    with_users: bool = Query(False, description="是否包含用户信息"),
    page: Optional[int] = Query(1, description="页码，从1开始", ge=1),
    page_size: Optional[int] = Query(10, description="每页数量", ge=1, le=100)
) -> PaginationResponse[WorkspaceDetailResponse]:
    """获取当前用户的工作空间列表，包含用户数量和角色信息
    
    Args:
        current_user: 当前用户
        page: 页码，从1开始
        page_size: 每页数量
        
    Returns:
        PaginationResponse: 分页响应，包含工作空间详细信息列表
    """
    # 计算skip和limit
    skip = (page - 1) * page_size
    
    # 获取工作空间列表和总数
    workspaces, total = await WorkspaceCore.get_user_workspaces(
        current_user,
        skip=skip,
        limit=page_size,
        with_users=with_users,
    )
    
    # 计算总页数
    total_pages = ceil(total / page_size)
    
    return PaginationResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=workspaces
    )

@router.put("/{workspace_id}", response_model=CommonResponse)
async def update_workspace(
    workspace_id: str,
    workspace_data: WorkspaceUpdate,
    user: UserModel = Depends(current_user)
) -> CommonResponse:
    """更新工作空间信息
    
    Args:
        workspace_id: 工作空间ID
        workspace_data: 要更新的工作空间数据
        user: 当前用户
        
    Returns:
        CommonResponse: 操作结果
    """
    # 获取工作空间
    workspace = await WorkspaceModel.get(workspace_id, fetch_links=True)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作空间不存在")
        
    # 更新工作空间
    try:
        workspace_core = WorkspaceCore(workspace=workspace)
        await workspace_core.update_workspace(
            user=user,
            workspace_data=workspace_data.model_dump()
        )
        return CommonResponse(message="工作空间更新成功")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        

@router.delete("/{workspace_id}", response_model=CommonResponse)
async def delete_workspace(
    workspace_id: str,
    user: UserModel = Depends(current_user)
) -> CommonResponse:
    """删除工作空间
    
    Args:
        workspace_id: 工作空间ID
        user: 当前用户
        
    Returns:
        CommonResponse: 操作结果
    """
    # 获取工作空间
    workspace = await WorkspaceModel.get(workspace_id, fetch_links=True)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作空间不存在")
        
    # 删除工作空间
    try:
        workspace_core = WorkspaceCore(workspace=workspace)
        await workspace_core.delete_workspace(user=user)
        return CommonResponse(message="工作空间删除成功")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
