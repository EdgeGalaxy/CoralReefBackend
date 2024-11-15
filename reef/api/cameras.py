from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
import cv2

from reef.core.cameras import CameraCore
from reef.models import WorkspaceModel, CameraModel, GatewayModel, DeploymentModel
from reef.schemas import CommonResponse
from reef.schemas.cameras import (
    CameraCreate,
    CameraResponse,
    CameraUpdate
)
from reef.schemas.deployments import DeploymentResponse
from reef.api._depends import check_user_has_workspace_permission, get_camera, get_gateway, get_workspace


router = APIRouter(
    prefix="/workspaces/{workspace_id}/cameras",
    tags=["cameras"],
    dependencies=[Depends(check_user_has_workspace_permission)]
)


@router.get("/", response_model=List[CameraResponse])
async def list_cameras(
    workspace: WorkspaceModel = Depends(get_workspace),
) -> List[CameraResponse]:
    cameras = await CameraCore.get_workspace_cameras(workspace=workspace)
    return [CameraResponse.db_to_schema(c) for c in cameras]


@router.post("/", response_model=CameraResponse)
async def create_camera(
    camera_data: CameraCreate,
    workspace: WorkspaceModel = Depends(get_workspace),
) -> CameraResponse:
    camera_core = await CameraCore.create_camera(
        camera_data=camera_data.model_dump(exclude_unset=True, exclude={'gateway_id'}),
        workspace=workspace,
        gateway=await get_gateway(camera_data.gateway_id) if camera_data.gateway_id else None
    )
    return CameraResponse.db_to_schema(camera_core.camera)


@router.put("/{camera_id}", response_model=CommonResponse)
async def update_camera(
    camera_data: CameraUpdate,
    camera: CameraModel = Depends(get_camera),
) -> CommonResponse:
    camera_core = CameraCore(camera=camera)
    await camera_core.update_camera(camera_data=camera_data.model_dump(exclude_unset=True))
    return CommonResponse(message="相机更新成功")


@router.delete("/{camera_id}", response_model=CommonResponse)
async def delete_camera(
    camera: CameraModel = Depends(get_camera),
) -> CommonResponse:
    camera_core = CameraCore(camera=camera)
    await camera_core.delete_camera()
    return CommonResponse(message="相机删除成功")


@router.get("/{camera_id}/deployments", response_model=List[DeploymentResponse])
async def list_camera_deployments(
    camera: CameraModel = Depends(get_camera),
) -> List[DeploymentResponse]:
    camera_core = CameraCore(camera=camera)
    deployments = await camera_core.get_deployments()
    return [DeploymentResponse.db_to_schema(d) for d in deployments]


@router.get("/{camera_id}/snapshot")
async def get_camera_snapshot(
    camera: CameraModel = Depends(get_camera),
):
    camera_core = CameraCore(camera=camera)
    snapshot = await camera_core.fetch_snapshot()
    # Convert snapshot to bytes for response
    success, encoded_image = cv2.imencode('.jpg', snapshot)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode camera snapshot")
    return Response(content=encoded_image.tobytes(), media_type="image/jpeg")
