from datetime import datetime
from typing import Dict, List
from enum import Enum
from beanie import Document, Link
from pydantic import BaseModel, Field

class Language(str, Enum):
    EN = "en"
    ZH = "zh"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]


class BlockTranslation(Document):
    """区块描述的翻译模型"""
    language: Language = Field(description="语言类型")
    human_friendly_block_name: str = Field(description="区块友好名称翻译")
    block_schema: Dict[str, Dict[str, str]] = Field(description="区块schema的翻译映射")
    manifest_type_identifier: str = Field(description="用于识别区块manifest的标识符")

    disabled: bool = Field(default=True, description="是否禁用")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Settings:
        name = "block_translations"



async def get_translated_blocks(blocks: List[BaseModel], language: Language = Language.EN):
    """获取指定语言的翻译版本"""
    for block in blocks:
        blocks_translation = await BlockTranslation.find_one(
            BlockTranslation.manifest_type_identifier == block.manifest_type_identifier,
            language=language,
            disabled=False
        )

        if blocks_translation:
            block.human_friendly_block_name = blocks_translation.human_friendly_block_name
            block.block_schema = blocks_translation.block_schema
        
    return blocks