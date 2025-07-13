import asyncio
import threading
from typing import Optional
from threading import Event
from fractions import Fraction

import cv2
import numpy as np
from loguru import logger
from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
)
from av import VideoFrame
from av import logging as av_logging

from reef.exceptions import RemoteCallError
from reef.utlis.cloud import sign_url_sync
from reef.models.cameras import CameraModel, CameraType
from reef.schemas.cameras import CameraWebRTCStreamRequest, CameraWebRTCStreamResponse


class CV2VideoSource:
    """基于CV2的视频源，支持不同类型的摄像头"""
    
    def __init__(self, camera: CameraModel):
        self.camera = camera
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self._last_frame: Optional[np.ndarray] = None
    
    def _get_video_path(self) -> str:
        """获取视频路径"""
        if self.camera.type == CameraType.FILE:
            return sign_url_sync(self.camera.path)
        else:
            return str(self.camera.path)
    
    def start(self):
        """启动视频源"""
        if self.is_running:
            return
        
        try:
            path = self._get_video_path()
            self.cap = cv2.VideoCapture(path)
            
            if not self.cap.isOpened():
                raise ValueError(f"无法打开视频源: {path}")
            
            self.is_running = True
            logger.info(f"视频源启动成功: {path}")
            
        except Exception as e:
            logger.error(f"启动视频源失败: {e}")
            raise
    
    def stop(self):
        """停止视频源"""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def get_frame(self) -> Optional[np.ndarray]:
        """获取视频帧"""
        if not self.is_running or not self.cap:
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self._last_frame = frame.copy()
                return frame
            else:
                # 如果读取失败，返回上一帧
                return self._last_frame
        except Exception as e:
            logger.error(f"读取视频帧失败: {e}")
            return self._last_frame
    
    def get_last_frame(self) -> Optional[np.ndarray]:
        """获取最后一帧"""
        return self._last_frame


class WebRTCVideoTrack(VideoStreamTrack):
    """WebRTC视频轨道，从CV2视频源获取帧"""
    
    def __init__(self, video_source: CV2VideoSource, fps: float = 30):
        super().__init__()
        self.video_source = video_source
        self.fps = int(fps)
        self._processed = 0
        self._last_frame: Optional[VideoFrame] = None
        self._av_logging_set = False
        self._active = True
    
    def close(self):
        """关闭视频轨道"""
        self._active = False
        self.video_source.stop()
    
    async def recv(self):
        """接收视频帧"""
        # 静音swscaler警告
        if not self._av_logging_set:
            av_logging.set_libav_level(av_logging.ERROR)
            self._av_logging_set = True
        
        if not self._active:
            raise Exception("视频轨道已关闭")
        
        self._processed += 1
        
        # 获取视频帧
        np_frame = self.video_source.get_frame()
        
        if np_frame is None:
            # 如果没有新帧，使用上一帧或创建默认帧
            if self._last_frame:
                new_frame = self._last_frame
            else:
                # 创建默认黑色帧
                default_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(default_frame, "等待视频流...", (10, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                new_frame = VideoFrame.from_ndarray(default_frame, format="bgr24")
        else:
            # 转换为VideoFrame
            new_frame = VideoFrame.from_ndarray(np_frame, format="bgr24")
            self._last_frame = new_frame
        
        # 设置时间戳
        try:
            new_frame.pts = self._processed
            new_frame.time_base = Fraction(1, self.fps)
        except Exception as e:
            logger.error(f'设置帧时间失败: {e}')
            new_frame.pts = self._processed
            new_frame.time_base = Fraction(1, 30)
        
        return new_frame


class WebRTCPeerConnection(RTCPeerConnection):
    """扩展的RTCPeerConnection，包含视频轨道管理"""
    
    def __init__(self, video_track: WebRTCVideoTrack, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_track = video_track
    
    async def close(self):
        """关闭连接"""
        if self.video_track:
            self.video_track.close()
        await super().close()


class WebRTCManager:
    """WebRTC连接管理器"""
    
    def __init__(self):
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event: Optional[Event] = None
        self.peer_connection: Optional[WebRTCPeerConnection] = None
        self.video_source: Optional[CV2VideoSource] = None
        self.video_track: Optional[WebRTCVideoTrack] = None
    
    def _start_event_loop(self, loop: asyncio.AbstractEventLoop):
        """启动异步事件循环"""
        asyncio.set_event_loop(loop)
        loop.run_forever()
    
    async def _create_peer_connection(self, config: CameraWebRTCStreamRequest, camera: CameraModel) -> WebRTCPeerConnection:
        """创建对等连接"""
        # 创建视频源
        self.video_source = CV2VideoSource(camera)
        self.video_source.start()
        
        # 创建视频轨道
        self.video_track = WebRTCVideoTrack(self.video_source, config.fps)
        
        # 创建WebRTC配置
        ice_servers = []
        if config.webrtc_turn_config:
            ice_servers.append(RTCIceServer(
                urls=config.webrtc_turn_config.urls,
                username=config.webrtc_turn_config.username,
                credential=config.webrtc_turn_config.credential,
            ))
        
        rtc_config = RTCConfiguration(iceServers=ice_servers) if ice_servers else None
        
        # 创建对等连接
        self.peer_connection = WebRTCPeerConnection(
            video_track=self.video_track,
            configuration=rtc_config
        )
        
        # 添加视频轨道
        self.peer_connection.addTrack(self.video_track)
        
        # 连接状态变化处理
        @self.peer_connection.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"连接状态变化: {self.peer_connection.connectionState}")
            if self.peer_connection.connectionState in {"failed", "closed"}:
                logger.info("WebRTC连接关闭")
                if self.video_track:
                    self.video_track.close()
                if self.stop_event:
                    self.stop_event.set()
                if self.video_source:
                    self.video_source.stop()
        
        # 设置远程描述并创建应答
        await self.peer_connection.setRemoteDescription(
            RTCSessionDescription(sdp=config.webrtc_offer.sdp, type=config.webrtc_offer.type)
        )
        
        answer = await self.peer_connection.createAnswer()
        await self.peer_connection.setLocalDescription(answer)
        
        logger.info(f"WebRTC连接创建成功，状态: {self.peer_connection.connectionState}")
        
        return self.peer_connection
    
    def create_webrtc_connection(self, config: CameraWebRTCStreamRequest, camera: CameraModel) -> CameraWebRTCStreamResponse:
        """创建WebRTC连接"""
        try:
            logger.info("开始创建WebRTC连接")
            
            # 创建新的异步事件循环和线程
            self.loop = asyncio.new_event_loop()
            self.thread = threading.Thread(
                target=self._start_event_loop, 
                args=(self.loop,), 
                daemon=True
            )
            self.thread.start()
            
            # 创建停止事件
            self.stop_event = Event()
            
            # 在新线程中创建对等连接
            future = asyncio.run_coroutine_threadsafe(
                self._create_peer_connection(config, camera),
                self.loop
            )
            
            peer_connection = future.result(timeout=10)  # 10秒超时
            
            logger.info("WebRTC连接创建成功")
            
            return CameraWebRTCStreamResponse(
                status="success",
                sdp=peer_connection.localDescription.sdp,
                type=peer_connection.localDescription.type,
                error=None
            )
            
        except Exception as e:
            logger.error(f"创建WebRTC连接失败: {e}")
            raise RemoteCallError(f"创建WebRTC连接失败: {e}")
    
    def get_stop_event(self) -> Optional[Event]:
        """获取停止事件"""
        return self.stop_event
    
    def cleanup(self):
        """清理资源"""
        if self.stop_event:
            self.stop_event.set()
        
        if self.peer_connection:
            try:
                if self.loop and not self.loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(
                        self.peer_connection.close(), 
                        self.loop
                    )
                    try:
                        future.result(timeout=5.0)
                    except:
                        pass
            except Exception as e:
                logger.warning(f"清理peer_connection时出错: {e}")
        
        if self.video_source:
            self.video_source.stop()
        
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except:
                pass
        
        logger.info("WebRTC资源清理完成")


def create_webrtc_connection(config: CameraWebRTCStreamRequest, camera: CameraModel) -> tuple[CameraWebRTCStreamResponse, WebRTCManager]:
    """创建WebRTC连接的便捷函数"""
    manager = WebRTCManager()
    result = manager.create_webrtc_connection(config, camera)
    return result, manager
