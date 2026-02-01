from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.enums import SourceType, ItemType


class SourceBase(BaseModel):
    name: str
    type: SourceType
    base_url: str
    target_item_types: List[ItemType]
    scrape_frequency: str = "MONTHLY"
    is_important: bool = False
    is_active: bool = True
    include_patterns: List[str] = []
    exclude_patterns: List[str] = []
    extra_data: Dict[str, Any] = {}
    notes: Optional[str] = None


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[SourceType] = None
    base_url: Optional[str] = None
    target_item_types: Optional[List[ItemType]] = None
    scrape_frequency: Optional[str] = None
    is_important: Optional[bool] = None
    is_active: Optional[bool] = None
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    extra_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class SourceResponse(BaseModel):
    id: UUID
    name: str
    type: SourceType
    base_url: str
    target_item_types: List[ItemType]
    scrape_frequency: str
    is_important: bool
    is_active: bool
    include_patterns: List[str]
    exclude_patterns: List[str]
    extra_data: Dict[str, Any]
    notes: Optional[str]
    last_scraped_at: Optional[datetime]
    urls_discovered_count: int
    items_extracted_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceListResponse(BaseModel):
    items: List[SourceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
