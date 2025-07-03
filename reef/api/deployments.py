import asyncio
from typing import List
from fastapi import APIRouter, Depends, Query

from reef.core.deployments import DeploymentCore
from reef.models import (
    WorkspaceModel, 
    DeploymentModel,
    WorkflowModel,
)
from reef.schemas import CommonResponse
from reef.schemas.deployments import (
    DeploymentCreate,
    DeploymentResponse,
    DeploymentUpdate,
    DeploymentDiffResponse,
    DeploymentOfferRequest,
    WebRTCOffer
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
    asyncio.create_task(DeploymentCore.sync_status(workspace))
    return [DeploymentResponse.db_to_schema(d) for d in deployments]


@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment_data: DeploymentCreate,
    workspace: WorkspaceModel = Depends(get_workspace),
) -> DeploymentResponse:
    deployment_core = await DeploymentCore.create_deployment(
        name=deployment_data.name,
        description=deployment_data.description,
        gateway=await get_gateway(deployment_data.gateway_id),
        cameras=await get_cameras(deployment_data.camera_ids),
        workflow=await get_workflow(deployment_data.workflow_id),
        parameters=deployment_data.parameters,
        workspace=workspace
    )
    return DeploymentResponse.db_to_schema(deployment_core.deployment)


@router.put("/{deployment_id}", response_model=CommonResponse)
async def update_deployment(
    deployment_data: DeploymentUpdate,
    deployment: DeploymentModel = Depends(get_deployment),
) -> CommonResponse:
    deployment_core = DeploymentCore(deployment=deployment)
    await deployment_core.update_deployment(
        update_data=deployment_data.model_dump(exclude_unset=True, exclude={'camera_ids'}),
        cameras=await get_cameras(deployment_data.camera_ids) if deployment_data.camera_ids else None
    )
    return CommonResponse(message="更新成功")


@router.delete("/{deployment_id}", response_model=CommonResponse)
async def delete_deployment(
    deployment: DeploymentModel = Depends(get_deployment),
) -> CommonResponse:
    deployment_core = DeploymentCore(deployment=deployment)
    await deployment_core.delete_deployment()
    return CommonResponse(message="删除成功")


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


@router.get("/{deployment_id}/metrics")
async def get_deployment_metrics(
    deployment: DeploymentModel = Depends(get_deployment),
    start_time: float = Query(None, description="开始时间戳（秒）"),
    end_time: float = Query(None, description="结束时间戳（秒）"),
    minutes: int = Query(5, description="最近几分钟的数据，当start_time和end_time为空时使用")
):
    """获取指定时间范围内的Pipeline指标数据"""
    deployment_core = DeploymentCore(deployment=deployment)
    return await deployment_core.get_metrics_timerange(start_time, end_time, minutes)


@router.post("/{deployment_id}/pause")
async def pause_deployment(
    deployment: DeploymentModel = Depends(get_deployment),
):
    deployment_core = DeploymentCore(deployment=deployment)
    status = await deployment_core.pause_pipeline()
    return CommonResponse(message="暂停成功" if status else "暂停失败")


@router.post("/{deployment_id}/resume")
async def resume_deployment(
    deployment: DeploymentModel = Depends(get_deployment),
):
    deployment_core = DeploymentCore(deployment=deployment)
    status = await deployment_core.resume_pipeline()
    return CommonResponse(message="恢复成功" if status else "恢复失败")


@router.post("/{deployment_id}/restart")
async def restart_deployment(
    deployment: DeploymentModel = Depends(get_deployment),
) -> CommonResponse:
    """
    重启部署的 pipeline，使用最新的 workflow 和 cameras 配置
    """
    deployment_core = DeploymentCore(deployment=deployment)
    _, message = await deployment_core.restart_pipeline()
    return CommonResponse(message=message)


@router.get("/{deployment_id}/compare", response_model=DeploymentDiffResponse)
async def compare_deployment_config(
    deployment: DeploymentModel = Depends(get_deployment),
) -> DeploymentDiffResponse:
    """
    比较 deployment 当前 workflow/cameras md5 与最新 workflow/cameras md5 是否一致
    """
    deployment_core = DeploymentCore(deployment=deployment)
    return await deployment_core.compare_config()


@router.post("/{deployment_id}/offer", response_model=WebRTCOffer)
async def offer_deployment(
    offer_request: DeploymentOfferRequest,
    deployment: DeploymentModel = Depends(get_deployment),
) -> WebRTCOffer:
    deployment_core = DeploymentCore(deployment=deployment)
    return await deployment_core.offer_pipeline(offer_request.model_dump())