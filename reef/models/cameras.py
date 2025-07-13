from datetime import datetime
from enum import Enum
from typing import Optional, Union

import cv2
import base64
import numpy as np
from pydantic import Field
from beanie import Document, Link
from reef.models.workspaces import WorkspaceModel
from reef.models.gateways import GatewayModel
from reef.utlis.cloud import sign_url
from reef.exceptions import RemoteCallError

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
    
    async def fetch_snapshot(self) -> str:
        """Fetch a snapshot from camera."""
        from reef.utlis.pipeline import PipelineClient
        # 如果 gateway 不为空且 type 为 USB，则使用 pipeline 方式
        if self.gateway and self.type == CameraType.USB:
            try:
                gateway_url = self.gateway.get_api_url()
                pipeline_client = PipelineClient(api_url=gateway_url)
                # 调用 pipeline 客户端的视频帧捕获接口
                result = await pipeline_client.capture_video_frame(video_source=self.path)
                if result.get('status') == 'success':
                    return result['image_base64']
                else:
                    raise RemoteCallError(f"获取视频帧失败: {result.get('error')}")
                    
            except Exception as e:
                raise RemoteCallError(f"获取视频帧失败: {e}")
        else:
            # 尝试使用 cv2.VideoCapture 读取视频帧
            try:
                # 根据类型处理路径
                if self.type == CameraType.FILE:
                    path = await sign_url(self.path)
                else:
                    path = str(self.path)
                
                cap = cv2.VideoCapture(path)
                
                if not cap.isOpened():
                    raise RemoteCallError("无法打开视频源")

                count = 0 
                while count < 5: 
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        count += 1
                    else:
                        break

                cap.release()
                
                if frame is not None:
                    # 将帧编码为JPEG格式
                    success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    if success:
                        # 转换为base64
                        image_base64 = base64.b64encode(buffer).decode('utf-8')
                        return image_base64
                    else:
                        raise RemoteCallError("无法编码图片为JPEG格式")
                else:
                    raise RemoteCallError("无法读取帧")
            except Exception as e:
                raise RemoteCallError(f"获取视频帧失败: {e}")
    
    async def fetch_webrtc_video_stream(self, webrtc_config: dict) -> dict:
        """Fetch a webrtc video stream from camera."""
        from reef.utlis.pipeline import PipelineClient
        from reef.utlis.webrtc import create_webrtc_connection

        # 对于有网关的 USB 摄像头，使用 pipeline 客户端
        if self.gateway and self.type == CameraType.USB:
            try:
                gateway_url = self.gateway.get_api_url()
                pipeline_client = PipelineClient(api_url=gateway_url)
                result = await pipeline_client.create_webrtc_video_stream(
                    video_source=self.path,
                    webrtc_config=webrtc_config,
                )   
                return result
            except Exception as e:
                raise RemoteCallError(f"获取视频流失败: {e}")
        else:
            # 对于其他类型的摄像头，使用新的 WebRTC 实现
            try:
                # 创建 WebRTC 连接
                result, manager = create_webrtc_connection(webrtc_config, self)
                
                return result
                    
            except Exception as e:
                raise RemoteCallError(f"获取视频流失败: {e}")

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
