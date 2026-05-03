from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    current_page: int
    per_page: int
    last_page: int
    total: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta
