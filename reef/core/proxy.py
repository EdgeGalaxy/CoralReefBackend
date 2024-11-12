from typing import Dict

from fastapi.responses import RedirectResponse
import requests
from loguru import logger
from asyncer import asyncify
from beanie.odm.fields import PydanticObjectId

from reef.models import GatewayModel, GatewayStatus
from reef.core.gateways import GatewayCore
from reef.schemas.proxy import PingpackData


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
                return await self.handle_redirect(data)
        except Exception as e:
            logger.exception(f"{self.url} 解析请求失败: {e}, data: {data}")

    async def handle_pingpack(self, data: Dict):
        logger.debug(f"解析请求 [pingpack] ->: {data}")

        pingpack_data = PingpackData(**data)
        gateway = await GatewayModel.find_one(
            GatewayModel.id == PydanticObjectId(pingpack_data.device_id),
            fetch_links=True
        )
        if gateway.status == GatewayStatus.DELETED:
            gateway.status = GatewayStatus.ONLINE
            await gateway.save()
        
        gateway_core = GatewayCore(gateway=gateway)

        gateway_data = {
            "status": GatewayStatus.ONLINE,
            "ip_address": pingpack_data.ip_address,
            "mac_address": pingpack_data.mac_address,
            "version": pingpack_data.inference_server_version,
        }
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