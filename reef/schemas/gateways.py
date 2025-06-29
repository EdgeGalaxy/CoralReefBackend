import re
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator

from reef.models.gateways import GatewayStatus, GatewayModel


class GatewayBase(BaseModel):
    """Base gateway schema with common fields"""
    name: str = Field(description="网关名称")
    description: str = Field(description="网关描述")
    version: str = Field(description="网关版本")
    platform: str = Field(description="网关平台")
    ip_address: Optional[str] = Field(default='', description="网关IP地址")
    mac_address: Optional[str] = Field(default='', description="网关MAC地址")

    @field_validator('mac_address')
    def validate_mac_address(cls, v):
        # 去掉冒号
        v = v.replace(':', '')
        if v and not re.match(r'^[0-9a-fA-F]{12}$', v):
            raise ValueError('Invalid MAC address')
        return v


class GatewayCreate(GatewayBase):
    """Schema for creating a new gateway"""
    id: str = Field(description="网关ID")


class GatewayUpdate(BaseModel):
    """Schema for updating an existing gateway"""
    name: Optional[str] = Field(default='', description="网关名称")
    description: Optional[str] = Field(default='', description="网关描述")


class GatewayResponse(GatewayBase):
    """Schema for gateway responses"""
    id: str = Field(description="网关ID")
    status: GatewayStatus = Field(description="网关状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    workspace_id: str = Field(description="所属工作空间ID")
    workspace_name: str = Field(description="所属工作空间名称")

    class Config:
        from_attributes = True
    
    @classmethod
    def db_to_schema(cls, db: GatewayModel) -> "GatewayResponse":
        return cls(
            id=str(db.id),
            name=db.name,
            description=db.description,
            workspace_id=str(db.workspace.id),
            workspace_name=db.workspace.name,
            version=db.version,
            platform=db.platform,
            ip_address=db.ip_address,
            mac_address=db.mac_address,
            status=db.status,
            created_at=db.created_at,
            updated_at=db.updated_at,
        )


class GatewayCommandResponse(BaseModel):
    """网关安装命令响应"""
    name: str
    description: str
    code_snippet: str
