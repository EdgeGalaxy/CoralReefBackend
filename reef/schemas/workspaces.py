from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from reef.models import WorkspaceRole, WorkspaceModel


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_users: int = 10


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    max_users: int
    owner_user_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def db_to_schema(cls, db: WorkspaceModel) -> "WorkspaceResponse":
        return cls(
            id=str(db.id),
            name=db.name,
            description=db.description,
            max_users=db.max_users,
            owner_user_id=str(db.owner_user.id),
            created_at=db.created_at,
            updated_at=db.updated_at,
        )