from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field
from beanie.odm.fields import PydanticObjectId

from reef.models.events import EventType


class EventBase(BaseModel):
    event_type: EventType
    details: Dict[str, Any]
    created_at: datetime


class EventRead(EventBase):
    id: PydanticObjectId = Field(..., alias="_id")
    workspace_id: PydanticObjectId
    gateway_id: Optional[PydanticObjectId] = None
    deployment_id: Optional[PydanticObjectId] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            PydanticObjectId: str
        } 