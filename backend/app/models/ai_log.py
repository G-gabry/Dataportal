from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin
from datetime import datetime


class AILog(Base, UUIDMixin):
    __tablename__ = "ai_logs"

    task_type = Column(String(50), nullable=False, index=True)
    model_used = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)

    # Related entity
    related_type = Column(String(50))
    related_id = Column(UUID(as_uuid=True))
    job_id = Column(UUID(as_uuid=True), ForeignKey("scrape_jobs.id", ondelete="SET NULL"), index=True)

    # Usage
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_usd = Column(Numeric(10, 6))
    latency_ms = Column(Integer)

    # Content (truncated for reference)
    input_preview = Column(Text)
    output_json = Column(JSONB)
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    job = relationship("ScrapeJob", back_populates="ai_logs")
