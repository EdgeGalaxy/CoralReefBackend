from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from reef.models import WorkspaceRole, WorkspaceModel, WorkspaceUserModel


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


class WorkspaceUsers(BaseModel):
    id: str
    username: str
    email: str
    role: WorkspaceRole
    join_at: datetime


class WorkspaceDetailResponse(BaseModel):
    """工作空间详细信息响应模型"""
    id: str
    name: str
    description: Optional[str] = None
    max_users: int
    owner_user_id: str
    user_count: int
    current_user_role: str
    created_at: datetime
    updated_at: datetime
    users: Optional[List[WorkspaceUsers]] = None