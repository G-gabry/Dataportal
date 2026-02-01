from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.enums import ItemType, ItemStatus


class ItemBase(BaseModel):
    item_type: ItemType
    data: Dict[str, Any] = {}
    custom_fields: Dict[str, Any] = {}
    notes: Optional[str] = None
    admin_notes: Optional[str] = None
    tags: List[str] = []


class ItemCreate(ItemBase):
    source_id: UUID
    discovered_url_id: Optional[UUID] = None


class ItemUpdate(BaseModel):
    data: Optional[Dict[str, Any]] = None
    field_status: Optional[Dict[str, str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    admin_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[ItemStatus] = None
    human_verified: Optional[bool] = None


class ItemResponse(BaseModel):
    id: UUID
    source_id: UUID
    discovered_url_id: Optional[UUID]
    item_type: ItemType
    data: Dict[str, Any]
    field_status: Dict[str, str]
    custom_fields: Dict[str, Any]
    notes: Optional[str]
    admin_notes: Optional[str]
    tags: Optional[List[str]]
    extraction_confidence: Optional[float]
    status: ItemStatus
    human_edited: bool
    human_verified: bool
    verified_by: Optional[UUID]
    verified_at: Optional[datetime]
    extracted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    items: List[ItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Public API schemas (simplified, no admin fields)
class ItemPublicResponse(BaseModel):
    id: UUID
    item_type: ItemType
    data: Dict[str, Any]
    custom_fields: Dict[str, Any]
    tags: Optional[List[str]]
    updated_at: datetime

    class Config:
        from_attributes = True
