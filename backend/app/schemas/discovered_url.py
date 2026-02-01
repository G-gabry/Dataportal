from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.enums import URLStatus, RelevanceStatus, PriorityLevel, ItemType


class DiscoveredURLBase(BaseModel):
    url: str
    url_path: Optional[str] = None


class DiscoveredURLUpdate(BaseModel):
    relevance: Optional[RelevanceStatus] = None
    relevance_reason: Optional[str] = None
    page_type: Optional[str] = None
    detected_item_types: Optional[List[ItemType]] = None
    content_tags: Optional[List[str]] = None
    priority: Optional[PriorityLevel] = None
    has_multiple_items: Optional[bool] = None
    human_verified: Optional[bool] = None
    human_notes: Optional[str] = None


class DiscoveredURLResponse(BaseModel):
    id: UUID
    source_id: UUID
    url: str
    url_path: Optional[str]

    # Classification
    relevance: RelevanceStatus
    relevance_score: Optional[float]
    relevance_reason: Optional[str]

    # Rich classification
    page_type: Optional[str]
    detected_item_types: Optional[List[ItemType]]
    content_tags: Optional[List[str]]
    priority: PriorityLevel
    has_multiple_items: bool

    # Content
    raw_markdown: Optional[str]
    content_hash: Optional[str]

    # Status
    status: URLStatus
    error_message: Optional[str]

    # Human review
    human_verified: bool
    human_notes: Optional[str]
    verified_by: Optional[UUID]
    verified_at: Optional[datetime]

    # Timestamps
    discovered_at: Optional[datetime]
    last_scraped_at: Optional[datetime]
    last_classified_at: Optional[datetime]

    class Config:
        from_attributes = True


class DiscoveredURLListResponse(BaseModel):
    items: List[DiscoveredURLResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
