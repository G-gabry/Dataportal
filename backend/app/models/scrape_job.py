from sqlalchemy import Column, String, Integer, Enum, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin
from app.models.enums import JobStatus
from datetime import datetime


class ScrapeJob(Base, UUIDMixin):
    __tablename__ = "scrape_jobs"

    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), index=True)

    job_type = Column(String(50), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)

    # Progress tracking
    current_step = Column(String(100))
    progress_percent = Column(Integer, default=0)

    # Stats
    urls_discovered = Column(Integer, default=0)
    urls_relevant = Column(Integer, default=0)
    urls_scraped = Column(Integer, default=0)
    items_extracted = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)

    # Cost tracking
    ai_tokens_used = Column(Integer, default=0)
    ai_cost_usd = Column(Numeric(10, 4), default=0)
    firecrawl_calls = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Errors
    error_log = Column(Text)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    source = relationship("Source", back_populates="scrape_jobs")
    created_by_user = relationship("User", back_populates="created_jobs")
    ai_logs = relationship("AILog", back_populates="job")
