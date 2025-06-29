from typing import List
from fastapi import APIRouter, Depends

from reef.core.gateways import GatewayCore
from reef.models import WorkspaceModel, GatewayModel
from reef.schemas import CommonResponse
from reef.schemas.cameras import CameraResponse
from reef.schemas.deployments import DeploymentResponse
from reef.schemas.gateways import (
    GatewayCreate,
    GatewayResponse,
    GatewayUpdate,
    GatewayCommandResponse
)
from reef.api._depends import check_user_has_workspace_permission, get_gateway, get_workspace



router = APIRouter(
    prefix="/workspaces/{workspace_id}/gateways",
    tags=["gateways"],
    dependencies=[Depends(check_user_has_workspace_permission)]
)


@router.get("/", response_model=List[GatewayResponse])
async def list_gateways(
    workspace: WorkspaceModel = Depends(get_workspace)
) -> List[GatewayResponse]:
    gateways = await GatewayCore.get_workspace_gateways(workspace=workspace)
    return [GatewayResponse.db_to_schema(g) for g in gateways]


@router.post("/", response_model=GatewayResponse)
async def create_gateway(
    gateway_data: GatewayCreate,
    workspace: WorkspaceModel = Depends(get_workspace),
) -> GatewayResponse:
    gateway_core = await GatewayCore.create_gateway(
        gateway_data=gateway_data.model_dump(exclude_none=True),
        workspace=workspace
    )
    return GatewayResponse.db_to_schema(gateway_core.gateway)


@router.put("/{gateway_id}", response_model=CommonResponse)
async def update_gateway(
    gateway_data: GatewayUpdate,
    gateway: GatewayModel = Depends(get_gateway),
) -> CommonResponse:
    gateway_core = GatewayCore(gateway=gateway)
    await gateway_core.update_gateway(gateway_data=gateway_data.model_dump(exclude_none=True))
    return CommonResponse(message="网关更新成功")


@router.delete("/{gateway_id}", response_model=CommonResponse)
async def delete_gateway(
    gateway: GatewayModel = Depends(get_gateway),
) -> CommonResponse:
    gateway_core = GatewayCore(gateway=gateway)
    await gateway_core.delete_gateway()
    return CommonResponse(message="网关删除成功")


@router.get("/{gateway_id}/cameras", response_model=List[CameraResponse])
async def list_gateway_cameras(
    gateway: GatewayModel = Depends(get_gateway),
) -> List[CameraResponse]:
    gateway_core = GatewayCore(gateway=gateway)
    cameras = await gateway_core.get_cameras()
    return [CameraResponse.db_to_schema(c) for c in cameras]


@router.get("/{gateway_id}/deployments", response_model=List[DeploymentResponse])
async def list_gateway_deployments(
    gateway: GatewayModel = Depends(get_gateway),
) -> List[DeploymentResponse]:
    gateway_core = GatewayCore(gateway=gateway)
    deployments = await gateway_core.get_deployments()
    return [DeploymentResponse.db_to_schema(d) for d in deployments]


@router.get("/install-command", response_model=GatewayCommandResponse)
async def get_gateway_install_command(
    workspace: WorkspaceModel = Depends(get_workspace),
) -> GatewayCommandResponse:
    # TODO: 后续可以从配置中读取
    return GatewayCommandResponse(
        name="新建网关",
        description="在设备上执行以下命令",
        code_snippet=f"curl -s https://loopeai.oss-cn-shanghai.aliyuncs.com/setup/init-bash/setup-client.sh | bash -s {workspace.id}"
    )
