from typing import Generic, TypeVar, Any

from pydantic import BaseModel

T = TypeVar("T")


class ResponseWrapper(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None


class PaginationData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool
