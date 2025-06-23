from typing import List, Optional

from beanie.odm.fields import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from loguru import logger

from reef.api._depends import get_workspace
from reef.models import EventModel, WorkspaceModel, EventType, DeploymentModel, GatewayModel
from reef.schemas.events import EventRead

router = APIRouter(prefix="/workspaces/{workspace_id}/events", tags=["Events"])


@router.get("/", response_model=List[EventRead])
async def list_events(
    workspace: WorkspaceModel = Depends(get_workspace),
    gateway_id: Optional[PydanticObjectId] = Query(None),
    deployment_id: Optional[PydanticObjectId] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    List events for the current workspace, with optional filtering by gateway or deployment.
    """
    query_conditions = [EventModel.workspace.id == workspace.id]

    if gateway_id:
        query_conditions.append(EventModel.gateway.id == gateway_id)

    if deployment_id:
        query_conditions.append(EventModel.deployment.id == deployment_id)

    events = (
        await EventModel.find(*query_conditions, fetch_links=True)
        .sort(-EventModel.created_at)
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    # Manually construct the response to include linked document IDs
    response = []
    for event in events:
        event_data = {
            "_id": event.id,
            "event_type": event.event_type,
            "details": event.details,
            "created_at": event.created_at,
            "workspace_id": event.workspace.id,
            "gateway_id": event.gateway.id if isinstance(event.gateway, GatewayModel) else None,
            "deployment_id": event.deployment.id if isinstance(event.deployment, DeploymentModel) else None,
        }
        response.append(EventRead.model_validate(event_data))

    return response 