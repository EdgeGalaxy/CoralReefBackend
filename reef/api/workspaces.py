from typing import List
from fastapi import APIRouter, Depends, HTTPException
from reef.core.workspaces import WorkspaceCore
from reef.models import UserModel, WorkspaceModel, WorkspaceRole
from reef.core.users import current_user
from reef.schemas import CommonResponse
from reef.schemas.workspaces import (
    WorkspaceCreate,
    WorkspaceResponse,
)

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


@router.get("/{workspace_id}/users/{owner_user_id}/{role}/{invited_user_id}", response_model=CommonResponse)
async def add_workspace_user(
    workspace_id: str,
    owner_user_id: str,
    role: WorkspaceRole,
    invited_user_id: str,
    user: UserModel = Depends(current_user)
) -> CommonResponse:
    workspace = await WorkspaceModel.get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作空间不存在")
    owner_user = await UserModel.get(owner_user_id)
    if not owner_user:  
        raise HTTPException(status_code=404, detail="邀请用户不存在")

    invited_user = await UserModel.get(invited_user_id)
    if not invited_user:
        raise HTTPException(status_code=404, detail="被邀请用户不存在")
    
    if invited_user_id != user.id:
        raise HTTPException(status_code=400, detail="邀请用户与当前登陆用户不一致")

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
    workspace = await WorkspaceModel.get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作空间不存在")
        
    user = await UserModel.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    workspace_core = WorkspaceCore(workspace=workspace)
    await workspace_core.remove_user(user=user)
    return CommonResponse(message="用户已从工作空间移除")


@router.get("/me", response_model=List[WorkspaceResponse])
async def get_my_workspaces(
    is_admin: bool = False,
    user: UserModel = Depends(current_user)
) -> List[WorkspaceResponse]:
    workspaces = await WorkspaceCore.get_user_workspaces(user=user, is_admin=is_admin)
    return [WorkspaceResponse.db_to_schema(w) for w in workspaces]
