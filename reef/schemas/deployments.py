from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from reef.models.deployments import OperationStatus, DeploymentModel


class DeploymentBase(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = {}


class DeploymentCreate(DeploymentBase):
    camera_ids: List[str]
    gateway_id: str
    workflow_id: str
    max_fps: Optional[int] = None


class DeploymentUpdate(BaseModel):
    name: Optional[str] = ''
    description: Optional[str] = ''
    camera_ids: Optional[List[str]] = []
    parameters: Optional[Dict[str, Any]] = {}
    max_fps: Optional[int] = None


class DeploymentResponse(DeploymentBase):
    id: str
    gateway_id: str
    gateway_name: str
    camera_ids: List[str]
    camera_names: List[str]
    workflow_id: str
    workflow_name: str
    pipeline_id: Optional[str]
    running_status: OperationStatus
    output_image_fields: List[str]
    workspace_id: str
    max_fps: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
    
    @classmethod
    def db_to_schema(cls, db: DeploymentModel) -> "DeploymentResponse":
        return cls(
            id=str(db.id),
            name=db.name,
            description=db.description,
            parameters=db.parameters,
            gateway_id=str(db.gateway.id),
            gateway_name=db.gateway.name,
            camera_ids=[str(c.id) for c in db.cameras],
            camera_names=[c.name for c in db.cameras],
            workflow_id=str(db.workflow.id),
            workflow_name=db.workflow.name,
            pipeline_id=db.pipeline_id,
            running_status=db.running_status,
            output_image_fields=db.output_image_fields,
            workspace_id=str(db.workspace.id),
            max_fps=db.max_fps,
            created_at=db.created_at,
            updated_at=db.updated_at
        )

class DeploymentDiffResponse(BaseModel):
    workflow_changed: bool
    cameras_changed: bool


class WebRTCOffer(BaseModel):
    type: str
    sdp: str

class WebRTCTURNConfig(BaseModel):
    urls: str
    username: str
    credential: str

class DeploymentOfferRequest(BaseModel):
    webrtc_offer: WebRTCOffer
    webrtc_turn_config: Optional[WebRTCTURNConfig] = None
    stream_output: Optional[List[Optional[str]]] = Field(default_factory=list)
    data_output: Optional[List[Optional[str]]] = Field(default_factory=list)
    webrtc_peer_timeout: float = 1
    webcam_fps: Optional[float] = 30
    processing_timeout: float = 0.1
    fps_probe_frames: int = 10
    max_consecutive_timeouts: int = 30
    min_consecutive_on_time: int = 5