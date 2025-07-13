from typing import Optional, Union, List
from datetime import datetime
from pydantic import BaseModel, Field

from reef.models.cameras import CameraType, CameraModel


class CameraBase(BaseModel):
    name: str = Field(description="相机名称")
    description: str = Field(description="相机描述")
    type: CameraType = Field(description="相机类型")
    path: Union[str, int] = Field(description="相机路径")


class CameraCreate(CameraBase):
    gateway_id: Optional[str] = None


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CameraVideoInfo(BaseModel):
    width: Optional[int] = Field(default=None, description="视频宽度")
    height: Optional[int] = Field(default=None, description="视频高度")
    fps: Optional[float] = Field(default=None, description="帧率")
    total_frames: Optional[int] = Field(default=None, description="总帧数")
    
    class Config:
        from_attributes = True


class WebRTCOffer(BaseModel):
    type: str = Field(description="WebRTC offer类型")
    sdp: str = Field(description="WebRTC SDP信息")

class WebRTCTURNConfig(BaseModel):
    urls: List[str] = Field(description="TURN服务器地址")
    username: str = Field(description="TURN服务器用户名")
    credential: str = Field(description="TURN服务器密码")


class CameraWebRTCStreamRequest(BaseModel):
    webrtc_offer: WebRTCOffer = Field(description="WebRTC offer信息")
    webrtc_turn_config: Optional[WebRTCTURNConfig] = None
    fps: Optional[float] = Field(default=30, description="视频帧率")
    processing_timeout: Optional[float] = Field(default=0.1, description="处理超时时间")
    max_consecutive_timeouts: Optional[int] = Field(default=30, description="最大连续超时次数")
    min_consecutive_on_time: Optional[int] = Field(default=5, description="最小连续正常时间")


class CameraSnapshotResponse(BaseModel):
    status: str = Field(description="状态")
    image_base64: Optional[str] = Field(default=None, description="base64编码的图片")
    width: Optional[int] = Field(default=None, description="图片宽度")
    height: Optional[int] = Field(default=None, description="图片高度")
    error: Optional[str] = Field(default=None, description="错误信息")


class CameraWebRTCStreamResponse(BaseModel):
    status: str = Field(description="状态")
    sdp: Optional[str] = Field(default=None, description="WebRTC SDP answer")
    type: Optional[str] = Field(default=None, description="WebRTC answer类型")
    error: Optional[str] = Field(default=None, description="错误信息")


class CameraResponse(CameraBase):
    id: str
    gateway_id: Optional[str] = None
    gateway_name: Optional[str] = None
    workspace_id: str
    workspace_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def db_to_schema(cls, db: CameraModel) -> "CameraResponse":
        return cls(
            id=str(db.id),
            name=db.name, 
            description=db.description, 
            type=db.type, 
            path=db.path, 
            gateway_id=str(db.gateway.id) if db.gateway else None, 
            gateway_name=db.gateway.name if db.gateway else None,
            workspace_id=str(db.workspace.id), 
            workspace_name=db.workspace.name,
            created_at=db.created_at, 
            updated_at=db.updated_at
        )
