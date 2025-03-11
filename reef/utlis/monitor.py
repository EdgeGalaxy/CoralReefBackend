import asyncio
from datetime import datetime, timedelta

from loguru import logger

from reef.models.gateways import GatewayModel, GatewayStatus
from reef.config import settings

# 默认超时时间为60秒，如果配置文件中未设置
GATEWAY_TIMEOUT = getattr(settings, 'GATEWAY_TIMEOUT', 60)


async def check_gateway_status():
    """检查网关状态的定时任务"""
    while True:
        try:
            # 获取所有在线的网关
            online_gateways = await GatewayModel.find(
                {"status": GatewayStatus.ONLINE}
            ).to_list()

            current_time = datetime.now()
            timeout_threshold = current_time - timedelta(seconds=GATEWAY_TIMEOUT * 3)

            for gateway in online_gateways:
                # 如果最后心跳时间超过阈值，将状态设置为离线
                if gateway.last_heartbeat < timeout_threshold:
                    gateway.status = GatewayStatus.OFFLINE
                    await gateway.save()
                    logger.warning(f'网关: {gateway.id} 检测上报时间超限，设置下线!')

        except Exception as e:
            logger.exception(f"检查网关状态时出错: {str(e)}")

        # 每60秒检查一次
        await asyncio.sleep(60)

async def start_gateway_monitor():
    """启动网关监控"""
    asyncio.create_task(check_gateway_status())