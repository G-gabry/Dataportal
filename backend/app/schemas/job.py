from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.enums import JobStatus


class ScrapeJobCreate(BaseModel):
    source_id: UUID
    job_type: str = "FULL_SCRAPE"  # FULL_SCRAPE, UPDATE_IMPORTANT, RE_SCRAPE


class SourceInfo(BaseModel):
    id: UUID
    name: str
    type: str
    base_url: str

    class Config:
        from_attributes = True


class ScrapeJobResponse(BaseModel):
    id: UUID
    source_id: Optional[UUID]
    job_type: str
    status: JobStatus

    # Source info
    source: Optional[SourceInfo] = None

    # Progress
    current_step: Optional[str]
    progress_percent: int

    # Stats
    urls_discovered: int
    urls_relevant: int
    urls_scraped: int
    items_extracted: int
    items_updated: int

    # Cost
    ai_tokens_used: int
    ai_cost_usd: float
    firecrawl_calls: int

    # Timing
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Error
    error_log: Optional[str]

    created_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class ScrapeJobListResponse(BaseModel):
    items: List[ScrapeJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
