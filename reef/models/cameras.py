from datetime import datetime
from enum import Enum
from typing import Optional, Union

import cv2
from pydantic import Field
from beanie import Document, Link
from reef.models.workspaces import WorkspaceModel
from reef.models.gateways import GatewayModel
from reef.utlis.cloud import sign_url

class CameraType(str, Enum):
    USB = "usb"
    RTSP = "rtsp"
    ONVIF = "onvif"
    AHD = "ahd"
    FILE = "file"
    URL = "url"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]


class CameraModel(Document):
    name: str = Field(description="摄像头名称")
    description: str = Field(description="摄像头描述")
    type: CameraType = Field(description="摄像头类型")
    gateway: Optional[Link[GatewayModel]] = Field(default=None, description="网关")
    path: Union[str, int] = Field(description="摄像头路径, 有网关ID时是与设备绑定的摄像头")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace: Link[WorkspaceModel] = Field(description="所属工作空间")

    class Settings:
        name = "cameras"
    
    async def fetch_snapshot(self) -> None:
        """Fetch a snapshot from camera."""
        # Create a mock image with numpy and cv2
        import numpy as np
        
        # Set image dimensions
        width = 640
        height = 480
        
        # Create base black image
        mock_image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add some random colored shapes
        # Draw a red rectangle
        cv2.rectangle(mock_image, (100, 100), (200, 200), (0, 0, 255), -1)
        
        # Draw a green circle
        cv2.circle(mock_image, (320, 240), 50, (0, 255, 0), -1)
        
        # Draw blue text
        cv2.putText(mock_image, "Mock Camera", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # Add some random noise
        noise = np.random.randint(0, 50, mock_image.shape, dtype=np.uint8)
        mock_image = cv2.add(mock_image, noise)
        
        return mock_image
    
    async def get_video_info(self) -> dict:
        """Get video information from camera."""
        # 只有特定类型的摄像头才获取视频信息
        if self.type not in [CameraType.FILE, CameraType.URL, CameraType.RTSP]:
            return {
                "width": None,
                "height": None,
                "fps": None,
                "total_frames": None
            }
        
        try:
            # 创建VideoCapture对象
            path = await sign_url(self.path) if self.type == CameraType.FILE else str(self.path)
            cap = cv2.VideoCapture(path)
            
            if not cap.isOpened():
                return {
                    "width": None,
                    "height": None,
                    "fps": None,
                    "total_frames": None
                }
            
            # 获取视频信息
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 释放VideoCapture对象
            cap.release()
            
            return {
                "width": width if width > 0 else None,
                "height": height if height > 0 else None,
                "fps": fps if fps > 0 else None,
                "total_frames": total_frames if total_frames > 0 else None
            }
        except Exception as e:
            # 如果获取失败，返回None值
            return {
                "width": None,
                "height": None,
                "fps": None,
                "total_frames": None
            }
