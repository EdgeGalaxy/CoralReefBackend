import asyncio
from datetime import datetime, timedelta

from loguru import logger

from reef.models.gateways import GatewayModel, GatewayStatus
from reef.models import DeploymentModel
from reef.core.deployments import DeploymentCore
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
                print(gateway.last_heartbeat, timeout_threshold)
                if gateway.last_heartbeat < timeout_threshold:
                    gateway.status = GatewayStatus.OFFLINE
                    await gateway.save()
                    logger.warning(f'网关: {gateway.id} 检测上报时间超限，设置下线!')
                else:
                    logger.info(f'网关: {gateway.id} 检测上报时间正常，继续运行!')

        except Exception as e:
            logger.exception(f"检查网关状态时出错: {str(e)}")

        # 每60秒检查一次
        await asyncio.sleep(60)

async def check_deployment_status():
    """检查所有部署服务状态的定时任务"""
    while True:
        try:
            # 获取所有部署服务
            deployments = await DeploymentModel.find(fetch_links=True).to_list()
            
            for deployment in deployments:
                try:
                    deployment_core = DeploymentCore(deployment)
                    running_status = await deployment_core.get_status()
                    logger.info(f'部署服务: {deployment.id} 状态为: {running_status.value}')
                except Exception as e:
                    logger.warning(f'部署服务: {deployment.id} 状态检查失败: {str(e)}')
                    continue

        except Exception as e:
            logger.exception(f"检查部署服务状态时出错: {str(e)}")

        # 每60秒检查一次
        await asyncio.sleep(60)

async def start_monitor():
    """启动所有监控任务"""
    asyncio.create_task(check_gateway_status())
    asyncio.create_task(check_deployment_status())