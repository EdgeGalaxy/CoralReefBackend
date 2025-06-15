from typing import Dict
from datetime import datetime

from fastapi.responses import RedirectResponse
import requests
from loguru import logger
from asyncer import asyncify
from beanie.odm.fields import PydanticObjectId

from reef.models import GatewayModel, GatewayStatus
from reef.core.gateways import GatewayCore
from reef.models.workspaces import WorkspaceModel
from reef.schemas.proxy import PingpackData
from reef.schemas.gateways import GatewayCreate


class ProxyCore:
    def __init__(self, url: str, method: str):
        self.url = url
        self.method = method

    async def dispatch(self, data: Dict):
        try:
            if 'inference-stats' in self.url:
                return await self.handle_pingpack(data)
            elif "usage/inference" in self.url:
                return await self.handle_inference_usage(data)
            elif "usage/plan" in self.url:
                return await self.handle_usage_plan(data)
            else:
                logger.warning(f"解析请求 [redirect] ->: {self.url} 不支持 {data} ")
                # return {"status": "success"}
                return await self.handle_redirect(data)
        except Exception as e:
            logger.exception(f"{self.url} 解析请求失败: {e}, data: {data}")

    async def handle_pingpack(self, data: Dict):
        logger.debug(f"解析请求 [pingpack] ->: {data}")
        if not data:
            logger.warning(f"pingpack 数据为空: {data}")
            return {"status": "success"}

        pingpack_data = PingpackData(**data)
        # 前置校验
        if not pingpack_data.device_id:
            logger.error(f"device_id 为空: {data}")
            raise ValueError("pingpack device_id 为空, 无法创建网关")
        
        # inference_server_id 不为空，且 包含 - 符号，第一个为workspace_id, 第二个为random_id
        if not pingpack_data.inference_server_id:
            logger.error(f"inference_server_id 为空: {data}")
            raise ValueError("pingpack inference_server_id 为空, 无法创建网关")

        if '-' not in pingpack_data.inference_server_id:
            logger.error(f"inference_server_id 格式错误: {data}")
            raise ValueError("pingpack inference_server_id 格式错误, 需要包含 - 符号, 无法创建网关")
        
        workspace_id, mac_address = pingpack_data.inference_server_id.split('-')
        
        gateway = await GatewayModel.find_one(
            GatewayModel.id == PydanticObjectId(pingpack_data.device_id),
            fetch_links=True
        )
        if not gateway:
            logger.info(f"网关 {pingpack_data.device_id} 不存在, 新建")
            workspace = await WorkspaceModel.find_one(
                WorkspaceModel.id == PydanticObjectId(workspace_id),
                fetch_links=True
            )

            if not workspace:
                logger.error(f"工作空间 {workspace_id} 不存在, 无法创建网关")
                raise ValueError(f"工作空间 {workspace_id} 不存在, 无法创建网关")
            # mac_address = pingpack_data.mac_address.replace(':', '')
            
            gateway_data = GatewayCreate(
                id=pingpack_data.device_id,
                name=mac_address,
                mac_address=mac_address,
                ip_address=pingpack_data.ip_address,
                version=pingpack_data.inference_server_version,
                platform=pingpack_data.platform,
                description=f"新建网关 {workspace.name}",
            )
            data = gateway_data.model_dump(exclude_none=True)
            # set status to online
            data['status'] = GatewayStatus.ONLINE
            data['last_heartbeat'] = datetime.now()
            gateway_core = await GatewayCore.create_gateway(
                gateway_data=data,
                workspace=workspace
            )
            gateway = gateway_core.gateway
            logger.info(f"新建网关 {gateway.id} 成功")

        gateway.status = GatewayStatus.ONLINE
        gateway_core = GatewayCore(gateway=gateway)

        gateway_data = {
            "status": GatewayStatus.ONLINE,
            "ip_address": pingpack_data.ip_address,
            "mac_address": mac_address,
            "version": pingpack_data.inference_server_version,
            "last_heartbeat": datetime.now()
        }
        logger.info(f"更新网关 {gateway.id} 状态为 {GatewayStatus.ONLINE}")
        await gateway_core.update_gateway(gateway_data=gateway_data)

    async def handle_inference_usage(self, data: Dict):
        logger.debug(f"解析请求 [usage-inference] ->: {data}")
        return {"status": "success"}

    async def handle_usage_plan(self, data: Dict):
        logger.debug(f"解析请求 [usage-plan] ->: {data}")
        return {"status": "success"}
    
    async def handle_redirect(self, data: Dict):
        logger.warning(f"解析请求 [redirect] ->: {self.url} {data}")
        if self.method == "POST":
            r = await asyncify(requests.request)(method=self.method, url=self.url, json=data)
            return r.json()
        elif self.method == "GET":
            r = RedirectResponse(url=self.url, status_code=307)
            return r
        else:
            raise ValueError(f"不支持的请求方法: {self.method}")