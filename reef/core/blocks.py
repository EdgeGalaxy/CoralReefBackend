from typing import List, Optional, Dict
from datetime import datetime
import requests
from asyncer import asyncify

from reef.models.blocks import BlockTranslation, Language
from reef.schemas.blocks import BlockTranslationCreate, BlockTranslationUpdate, BlockTranslationSync

class BlockCore:
    @staticmethod
    async def create_block_translation(block: BlockTranslationCreate) -> BlockTranslation:
        """创建区块翻译"""
        existing = await BlockCore.get_block_by_identifier_and_language(
            block.manifest_type_identifier,
            block.language
        )
        if existing:
            raise ValueError("Block translation already exists")

        block_doc = BlockTranslation(
            **block.model_dump(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await block_doc.insert()
        return block_doc

    @staticmethod
    async def get_block_translations(
        language: Optional[Language] = None,
        disabled: Optional[bool] = None
    ) -> List[BlockTranslation]:
        """获取区块翻译列表"""
        query = {}
        if language:
            query["language"] = language
        if disabled is not None:
            query["disabled"] = disabled
        
        return await BlockTranslation.find(query).to_list()

    @staticmethod
    async def get_block_translation(block_id: str) -> Optional[BlockTranslation]:
        """获取特定区块翻译"""
        return await BlockTranslation.get(block_id)

    @staticmethod
    async def get_block_by_identifier_and_language(
        identifier: str,
        language: Language
    ) -> Optional[BlockTranslation]:
        """根据标识符和语言获取区块翻译"""
        return await BlockTranslation.find_one(
            BlockTranslation.manifest_type_identifier == identifier,
            BlockTranslation.language == language
        )

    @staticmethod
    async def update_block_translation(
        block_id: str,
        block: BlockTranslationUpdate
    ) -> Optional[BlockTranslation]:
        """更新区块翻译"""
        existing = await BlockTranslation.get(block_id)
        if not existing:
            return None

        update_data = block.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
        
        await existing.update({"$set": update_data})
        return await BlockTranslation.get(block_id)

    @staticmethod
    async def delete_block_translation(block_id: str) -> bool:
        """删除区块翻译"""
        existing = await BlockTranslation.get(block_id)
        if not existing:
            return False
        await existing.delete()
        return True

    @staticmethod
    async def sync_block_translations(sync_data: BlockTranslationSync) -> List[BlockTranslation]:
        """同步第三方接口的区块数据"""
        response = await asyncify(requests.get)(sync_data.source_url)
        
        if response.status_code != 200:
            raise ValueError("Failed to fetch data from source")
        
        blocks = response.json()
        synced_blocks = []
        
        for block in blocks:
            block_doc = BlockTranslation(
                language=sync_data.language,
                human_friendly_block_name=block["human_friendly_block_name"],
                block_schema=block["block_schema"],
                manifest_type_identifier=block["manifest_type_identifier"],
                disabled=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            await block_doc.insert()
            synced_blocks.append(block_doc)
            
        return synced_blocks
