from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional

from reef.core.blocks import BlockCore
from reef.models.blocks import Language
from reef.schemas.blocks import (
    BlockTranslationCreate,
    BlockTranslationUpdate,
    BlockTranslationResponse,
    BlockTranslationSync,
    BlockTranslationPaginatedResponse,
    PaginationParams
)


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
    page: Optional[int] = Query(1, ge=1, description="页码"),
    page_size: Optional[int] = Query(10, ge=1, le=100, description="每页数量"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
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
    return updated_block


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block_translation(block_id: str):
    """删除区块翻译"""
    if not await BlockCore.delete_block_translation(block_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block translation not found"
        )


@router.post("/sync", response_model=List[BlockTranslationResponse])
async def sync_block_translations(sync_data: BlockTranslationSync):
    """同步第三方接口的区块数据"""
    try:
        return await BlockCore.sync_block_translations(sync_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
