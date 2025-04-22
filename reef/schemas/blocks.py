from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from reef.models.blocks import Language

class BlockTranslationBase(BaseModel):
    """区块翻译基础模型"""
    language: Language = Field(description="语言类型")
    human_friendly_block_name: str = Field(description="区块友好名称翻译")
    block_schema: Dict = Field(description="区块schema的翻译映射")
    manifest_type_identifier: str = Field(description="用于识别区块manifest的标识符")
    disabled: bool = Field(default=False, description="是否禁用")

class BlockTranslationCreate(BlockTranslationBase):
    """创建区块翻译请求模型"""
    pass

class BlockTranslationUpdate(BaseModel):
    """更新区块翻译请求模型"""
    language: Optional[Language] = None
    human_friendly_block_name: Optional[str] = None
    block_schema: Optional[Dict] = None
    manifest_type_identifier: Optional[str] = None
    disabled: Optional[bool] = None

class BlockTranslationResponse(BlockTranslationBase):
    """区块翻译响应模型"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def db_to_schema(cls, db: "BlockTranslation") -> "BlockTranslationResponse":
        return cls(
            id=str(db.id),
            language=db.language,
            human_friendly_block_name=db.human_friendly_block_name,
            block_schema=db.block_schema,
            manifest_type_identifier=db.manifest_type_identifier,
            disabled=db.disabled,
            created_at=db.created_at,
            updated_at=db.updated_at
        )

class BlockTranslationSync(BaseModel):
    """区块翻译同步请求模型"""
    source_url: str = "https://detect.roboflow.com/workflows/blocks/describe"
    language: Language = Language.ZH
