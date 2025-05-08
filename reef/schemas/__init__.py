from typing import TypeVar, Generic, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class CommonResponse(BaseModel):
    message: str


class PaginationResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[T]


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")