from typing import Optional, Union
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
