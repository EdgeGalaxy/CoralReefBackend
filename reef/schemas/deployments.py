from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from reef.models.deployments import OperationStatus, DeploymentModel


class DeploymentBase(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = {}


class DeploymentCreate(DeploymentBase):
    cameras_ids: List[str]


class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    camera_ids: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None


class DeploymentResponse(DeploymentBase):
    id: str
    gateway_id: str
    gateway_name: str
    camera_ids: List[str]
    camera_names: List[str]
    workflow_id: str
    workflow_name: str
    pipeline_id: Optional[str]
    running_status: OperationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
    
    @classmethod
    def db_to_schema(cls, db: DeploymentModel) -> "DeploymentResponse":
        return cls(
            id=str(db.id),
            name=db.name,
            description=db.description,
            parameters=db.parameters,
            gateway_id=str(db.gateway.id),
            gateway_name=db.gateway.name,
            camera_ids=[str(c.id) for c in db.cameras],
            camera_names=[c.name for c in db.cameras],
            workflow_id=str(db.workflow.id),
            workflow_name=db.workflow.name,
            pipeline_id=db.pipeline_id,
            running_status=db.running_status,
            created_at=db.created_at,
            updated_at=db.updated_at
        )
