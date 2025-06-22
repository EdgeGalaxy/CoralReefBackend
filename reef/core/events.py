from typing import Optional, Dict, Any

from loguru import logger

from reef.models import EventModel, EventType, WorkspaceModel, GatewayModel, DeploymentModel


class EventLogger:
    @staticmethod
    async def log(
        event_type: EventType,
        workspace: WorkspaceModel,
        gateway: Optional[GatewayModel] = None,
        deployment: Optional[DeploymentModel] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        try:
            event = EventModel(
                event_type=event_type,
                workspace=workspace,
                gateway=gateway,
                deployment=deployment,
                details=details or {},
            )
            await event.insert()
            logger.info(f"Logged event: {event_type.value} for workspace {workspace.id}")
        except Exception as e:
            logger.exception(f"Failed to log event {event_type.value}: {e}") 