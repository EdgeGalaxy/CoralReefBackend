from typing import TypeVar, Generic, List
from pydantic import BaseModel


class CommonResponse(BaseModel):
    message: str

T = TypeVar('T')

class PaginationResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[T]
