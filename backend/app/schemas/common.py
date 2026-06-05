from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = ""


class ErrorDetail(BaseModel):
    code: str
    message: str


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
