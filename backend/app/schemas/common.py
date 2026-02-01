from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional
from uuid import UUID

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    success: bool = True


class IDResponse(BaseModel):
    """Response with just an ID"""
    id: UUID
