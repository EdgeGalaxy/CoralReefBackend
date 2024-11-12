from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class PingpackData(BaseModel):
    """Pingpack data schema for device information and inference results"""
    api_key: Optional[str] = Field(default=None, description="API密钥")
    timestamp: str = Field(description="时间戳")
    device_id: str = Field(description="设备ID")
    inference_server_id: str = Field(description="推理服务器ID")
    inference_server_version: str = Field(description="推理服务器版本")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    platform: str = Field(description="平台")
    platform_release: str = Field(description="平台发行版本")
    platform_version: str = Field(description="平台详细版本")
    architecture: str = Field(description="系统架构")
    hostname: str = Field(description="主机名")
    ip_address: str = Field(description="IP地址")
    mac_address: str = Field(description="MAC地址")
    processor: str = Field(description="处理器类型")
    inference_results: List[Dict] = Field(default_factory=list, description="推理结果列表")