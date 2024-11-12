from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query

from reef.core.deployments import DeploymentCore
from reef.models import (
    WorkspaceModel, 
    DeploymentModel,
    GatewayModel,
    CameraModel,
    WorkflowModel
)
from reef.schemas import CommonResponse
from reef.schemas.deployments import (
    DeploymentCreate,
    DeploymentResponse,
    DeploymentUpdate
)
from reef.api._depends import (
    check_user_has_workspace_permission,
    get_deployment,
    get_gateway,
    get_workflow,
    get_cameras,
    get_workspace
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/deployments",
    tags=["deployments"],
    dependencies=[Depends(check_user_has_workspace_permission)]
)


@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(
    workspace: WorkspaceModel = Depends(get_workspace),
) -> List[DeploymentResponse]:
    deployments = await DeploymentCore.get_workspace_deployments(workspace=workspace)
    return [DeploymentResponse.db_to_schema(d) for d in deployments]


@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment_data: DeploymentCreate,
    workspace: WorkspaceModel = Depends(get_workspace),
    gateway: GatewayModel = Depends(get_gateway),
    workflow: WorkflowModel = Depends(get_workflow),
) -> DeploymentResponse:
    deployment_core = await DeploymentCore.create_deployment(
        name=deployment_data.name,
        description=deployment_data.description,
        gateway=gateway,
        cameras=await get_cameras(deployment_data.cameras_ids),
        workflow=workflow,
        parameters=deployment_data.parameters,
        workspace=workspace
    )
    return DeploymentResponse.db_to_schema(deployment_core.deployment)


@router.put("/{deployment_id}", response_model=CommonResponse)
async def update_deployment(
    deployment_data: DeploymentUpdate,
    deployment: DeploymentModel = Depends(get_deployment),
    cameras: List[CameraModel] = Depends(get_cameras),
) -> CommonResponse:
    deployment_core = DeploymentCore(deployment=deployment)
    await deployment_core.update_deployment(
        update_data=deployment_data.model_dump(exclude_unset=True, exclude={'camera_ids'}),
        cameras=cameras
    )
    return CommonResponse(message="部署更新成功")


@router.delete("/{deployment_id}", response_model=CommonResponse)
async def delete_deployment(
    deployment: DeploymentModel = Depends(get_deployment),
) -> CommonResponse:
    deployment_core = DeploymentCore(deployment=deployment)
    await deployment_core.delete_deployment()
    return CommonResponse(message="部署删除成功")


@router.get("/{deployment_id}/status")
async def get_deployment_status(
    deployment: DeploymentModel = Depends(get_deployment),
):
    deployment_core = DeploymentCore(deployment=deployment)
    return await deployment_core.get_status()


@router.get("/{deployment_id}/results")
async def get_deployment_results(
    deployment: DeploymentModel = Depends(get_deployment),
):
    deployment_core = DeploymentCore(deployment=deployment)
    return await deployment_core.get_results()
