from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TemplateBase(BaseModel):
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    tags: List[str] = Field(default=[], description="标签")
    is_public: bool = Field(default=False, description="是否公开")

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(TemplateBase):
    pass

class TemplateResponse(TemplateBase):
    id: str = Field(..., description="模板ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    usage_count: int = Field(..., description="使用次数")
    creator: dict = Field(..., description="创建者信息")

    @classmethod
    def db_to_schema(cls, template):
        return cls(
            id=str(template.id),
            name=template.name,
            description=template.description,
            is_public=template.is_public,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
            usage_count=template.usage_count,
            tags=template.tags,
            creator={
                "id": str(template.creator.id),
                "username": template.creator.username
            }
        )

class TemplatePublish(BaseModel):
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    tags: List[str] = Field(default=[], description="标签")
    is_public: bool = Field(default=False, description="是否公开")


class WorkflowSync(BaseModel):
    workflow_id: str = Field(..., description="Roboflow workflow id")
    project_id: Optional[str] = Field(default=None, description="Roboflow project id")
    api_key: Optional[str] = Field(default=None, description="Roboflow API key")


class TemplateFork(BaseModel):
    target_workspace_id: str = Field(..., description="目标工作空间ID") 