from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from copy import deepcopy

from reef.core.blocks import BlockCore
from reef.schemas import CommonResponse
from reef.schemas.blocks import (
    BlockTranslationCreate,
    BlockTranslationUpdate,
    BlockTranslationResponse,
    BlockTranslationSync,
    BlockTranslationPaginatedResponse,
    PaginationParams
)
from reef.utlis.roboflow import get_base_blocks_describe
from reef.models.blocks import BlockTranslation


router = APIRouter(prefix="/workflows/blocks", tags=["blocks"])


@router.post("/", response_model=BlockTranslationResponse, status_code=status.HTTP_201_CREATED)
async def create_block_translation(block: BlockTranslationCreate):
    """创建区块翻译"""
    try:
        return await BlockCore.create_block_translation(block)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=BlockTranslationPaginatedResponse)
async def list_block_translations(
    page: Optional[int] = Query(None, ge=1, description="页码"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="每页数量"),
    sort_by: Optional[str] = Query('disabled', description="排序字段"),
    sort_desc: bool = Query(False, description="是否降序"),
    disabled: Optional[bool] = None
):
    """获取区块翻译列表"""
    pagination = PaginationParams(page=page, page_size=page_size) if page and page_size else None
    blocks = await BlockCore.get_block_translations(
        pagination=pagination,
        disabled=disabled,
        sort_by=sort_by,
        sort_desc=sort_desc
    )
    return blocks


@router.get("/{block_id}", response_model=BlockTranslationResponse)
async def get_block_translation(block_id: str):
    """获取特定区块翻译"""
    block = await BlockCore.get_block_translation(block_id)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block translation not found"
        )
    return block


@router.put("/{block_id}", response_model=BlockTranslationResponse)
async def update_block_translation(block_id: str, block: BlockTranslationUpdate):
    """更新区块翻译"""
    updated_block = await BlockCore.update_block_translation(block_id, block)
    if not updated_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block translation not found"
        )
    return BlockTranslationResponse.db_to_schema(updated_block)


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block_translation(block_id: str):
    """删除区块翻译"""
    if not await BlockCore.delete_block_translation(block_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block translation not found"
        )


@router.post("/sync", response_model=CommonResponse)
async def sync_block_translations(sync_data: BlockTranslationSync):
    """同步第三方接口的区块数据"""
    try:
        await BlockCore.sync_block_translations(sync_data)
        return CommonResponse(message="同步成功")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )


@router.patch("/{block_id}/toggle", response_model=BlockTranslationResponse)
async def toggle_block_status(block_id: str):
    """切换区块启用/禁用状态"""
    try:
        block = await BlockCore.toggle_block_status(block_id)
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Block translation not found"
            )
        return BlockTranslationResponse.db_to_schema(block)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/describe/all")
async def get_blocks_describe(disabled: bool = Query(None, description="是否禁用")):
    """获取区块描述信息，包含翻译后的 schema"""
    # 获取所有区块翻译
    if disabled is None:
        blocks = await BlockTranslation.find().to_list()
    else:
        blocks = await BlockTranslation.find({'disabled': disabled}).to_list()
    
    # 创建 manifest_type_identifier 到 block_schema 的映射
    identifier_block_mapper = {
        block.manifest_type_identifier: block.block_schema
        for block in blocks
    }
    
    _describe_blocks = []
    describe = await get_base_blocks_describe()
    for block in describe['blocks']:
        _block = deepcopy(block)
        manifest_type_identifier = block['manifest_type_identifier']
        if manifest_type_identifier not in identifier_block_mapper:
            continue
        _block['block_schema'] = identifier_block_mapper[manifest_type_identifier]
        _describe_blocks.append(_block)
    
    return {
        'blocks': _describe_blocks,
        'kinds_connections': describe['kinds_connections']
    }
