from typing import List
from fastapi import Depends, HTTPException
from beanie import PydanticObjectId

from reef.models import UserModel
from reef.core.users import current_user

from reef.models import WorkspaceUserModel, GatewayModel, WorkspaceModel, DeploymentModel, CameraModel, WorkflowModel, GatewayStatus, MLModelModel, WorkflowTemplateModel


async def check_user_has_workspace_permission(workspace_id: str, user: UserModel = Depends(current_user)):
    workspace_user = await WorkspaceUserModel.find_one(
        WorkspaceUserModel.user.id == user.id,
        WorkspaceUserModel.workspace.id == PydanticObjectId(workspace_id)
    )
    if not workspace_user:
        raise HTTPException(status_code=403, detail="用户没有权限访问该工作空间")
    
    return workspace_user.workspace


async def get_gateway(gateway_id: str) -> GatewayModel:
    gateway = await GatewayModel.get(gateway_id, fetch_links=True)
    if not gateway:
        raise HTTPException(status_code=404, detail="网关不存在")

    if gateway.status == GatewayStatus.DELETED:
        raise HTTPException(status_code=404, detail="网关不存在")
    
    return gateway


async def get_deployment(deployment_id: str) -> DeploymentModel:
    deployment = await DeploymentModel.get(deployment_id, fetch_links=True)
    if not deployment:
        raise HTTPException(status_code=404, detail="部署不存在")
    
    return deployment


async def get_camera(camera_id: str) -> CameraModel:
    camera = await CameraModel.get(camera_id, fetch_links=True)
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头不存在")
    
    return camera


async def get_workspace(workspace_id: str) -> WorkspaceModel:
    workspace = await WorkspaceModel.get(workspace_id, fetch_links=True)
    if not workspace:
        raise HTTPException(status_code=404, detail="工作空间不存在")
    
    return workspace


async def get_workflow(workflow_id: str) -> WorkflowModel:
    workflow = await WorkflowModel.get(workflow_id, fetch_links=True)
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    return workflow


async def get_cameras(camera_ids: List[str]) -> List[CameraModel]:
    camera_ids = [PydanticObjectId(id) for id in camera_ids]
    cameras = await CameraModel.find({"_id": {"$in": camera_ids}}, fetch_links=True).to_list()
    if len(cameras) != len(camera_ids):
        raise HTTPException(status_code=404, detail="摄像头不存在")
    
    return cameras  


async def get_ml_model(model_id: str) -> MLModelModel:
    model = await MLModelModel.get(model_id, fetch_links=True)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    return model


async def get_template_with_user_check(template_id: str, user: UserModel = Depends(current_user)) -> WorkflowTemplateModel:
    template = await WorkflowTemplateModel.get(template_id, fetch_links=True)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if template.creator.id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此模板")
    return template


async def get_template(template_id: str) -> WorkflowTemplateModel:
    """获取模板"""
    template = await WorkflowTemplateModel.get(template_id, fetch_links=True)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template