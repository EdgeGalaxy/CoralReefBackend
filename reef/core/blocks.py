from typing import List, Optional, Dict
from datetime import datetime
import requests
from asyncer import asyncify

from reef.models.blocks import BlockTranslation, Language
from reef.schemas.blocks import (BlockTranslationCreate, BlockTranslationUpdate, BlockTranslationSync,
    PaginationParams, BlockTranslationPaginatedResponse, BlockTranslationResponse)

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
        pagination: Optional[PaginationParams] = None,
        disabled: Optional[bool] = None,
        sort_by: Optional[str] = 'sync_at',
        sort_desc: bool = True
    ) -> BlockTranslationPaginatedResponse:
        """获取区块翻译列表"""
        query = {}
        if disabled is not None:
            query["disabled"] = disabled
        
        # 构建查询
        find_query = BlockTranslation.find(query)
        
        # 计算总记录数
        total = await find_query.count()
        
        # 添加排序
        if sort_by:
            find_query = find_query.sort(
                (sort_by, -1) if sort_desc else (sort_by, 1)
            )
        
        # 如果提供了分页参数，则应用分页
        if pagination:
            total_pages = (total + pagination.page_size - 1) // pagination.page_size
            skip = (pagination.page - 1) * pagination.page_size
            find_query = find_query.skip(skip).limit(pagination.page_size)
            blocks = await find_query.to_list()
            
            return BlockTranslationPaginatedResponse(
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                items=[BlockTranslationResponse.db_to_schema(block) for block in blocks]
            )
        else:
            # 如果没有分页参数，返回所有记录
            blocks = await find_query.to_list()
            return BlockTranslationPaginatedResponse(
                total=total,
                page=1,
                page_size=total,
                total_pages=1,
                items=[BlockTranslationResponse.db_to_schema(block) for block in blocks]
            )

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
    def _compare_and_update_properties(existing_props: dict, new_props: dict) -> tuple[dict, bool]:
        """比较并更新属性，返回更新后的属性和是否有变化"""
        updated_props = existing_props.copy()
        has_changes = False

        for prop_name, new_prop_value in new_props.items():
            # 处理新属性
            if prop_name not in existing_props:
                updated_props[prop_name] = new_prop_value
                has_changes = True
                continue

            # 处理已存在的属性
            existing_prop = existing_props[prop_name]
            for field_name, field_value in new_prop_value.items():
                # 检查字段是否有变化
                if field_name not in existing_prop or existing_prop[field_name] != field_value:
                    updated_props[prop_name].update({field_name: field_value})
                    has_changes = True

        return updated_props, has_changes

    @staticmethod
    async def sync_block_translations(sync_data: BlockTranslationSync) -> List[BlockTranslation]:
        """同步第三方接口的区块数据"""
        response = await asyncify(requests.post)(sync_data.source_url)
        
        if response.status_code != 200:
            raise ValueError("Failed to fetch data from source")
        
        source_blocks = response.json()['blocks']
        current_time = datetime.now()
        
        # 获取所有已存在的区块
        existing_blocks = await BlockTranslation.find({
            "manifest_type_identifier": {"$in": [block["manifest_type_identifier"] for block in source_blocks]},
            "language": sync_data.language
        }).to_list()
        
        existing_map = {block.manifest_type_identifier: block for block in existing_blocks}
        blocks_to_insert = []
        
        for block in source_blocks:
            if block["manifest_type_identifier"] in existing_map:
                # 更新已存在的区块
                existing = existing_map[block["manifest_type_identifier"]]
                
                # 比较并更新属性
                existing_props = existing.block_schema.get("properties", {})
                new_props = block["block_schema"].get("properties", {})
                updated_props, props_changed = BlockCore._compare_and_update_properties(
                    existing_props, new_props
                )

                other_fields_changed = existing.execution_engine_compatibility != block.get("execution_engine_compatibility", '')

                # 如果有任何变化，更新区块
                if props_changed or other_fields_changed:
                    update_data = {
                        "human_friendly_block_name": block["human_friendly_block_name"],
                        "block_schema": {
                            **block["block_schema"],
                            "properties": updated_props
                        },
                        "execution_engine_compatibility": block.get("execution_engine_compatibility", ''),
                        "sync_at": current_time
                    }
                    # 使用 find_one(...).update 进行更新
                    await BlockTranslation.find_one(
                        BlockTranslation.id == existing.id
                    ).update({"$set": update_data})
                    
            else:
                # 创建新区块
                block_doc = BlockTranslation(
                    language=sync_data.language,
                    human_friendly_block_name=block["human_friendly_block_name"],
                    block_schema=block["block_schema"],
                    manifest_type_identifier=block["manifest_type_identifier"],
                    execution_engine_compatibility=block.get("execution_engine_compatibility", ''),
                    disabled=True,
                    created_at=current_time,
                    updated_at=current_time,
                    sync_at=current_time
                )
                blocks_to_insert.append(block_doc)
        
        # 批量插入新区块
        if blocks_to_insert:
            await BlockTranslation.insert_many(blocks_to_insert)
        return True

    @staticmethod
    async def toggle_block_status(block_id: str) -> Optional[BlockTranslation]:
        """切换区块的启用/禁用状态"""
        existing = await BlockTranslation.get(block_id)
        if not existing:
            return None

        # 切换状态
        update_data = {
            "disabled": not existing.disabled,
            "updated_at": datetime.now()
        }
        
        await existing.update({"$set": update_data})
        return await BlockTranslation.get(block_id)
