from sqlalchemy import Column, String, Boolean, Integer, Enum, DateTime, ForeignKey, Text, ARRAY, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin
from app.models.enums import URLStatus, RelevanceStatus, PriorityLevel, ItemType

# Create PostgreSQL ENUM type that matches the database
item_type_enum = ENUM('PROGRAM', 'SCHOLARSHIP', 'CONFERENCE', 'EXCHANGE', name='item_type', create_type=False)


class DiscoveredURL(Base, UUIDMixin):
    __tablename__ = "discovered_urls"

    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)

    url = Column(String(2000), nullable=False)
    url_path = Column(String(1000))

    # Classification Layer 1 (relevant or not)
    relevance = Column(Enum(RelevanceStatus), default=RelevanceStatus.PENDING, index=True)
    relevance_score = Column(Numeric(5, 2))
    relevance_reason = Column(Text)

    # Classification Layer 2 (detailed classification for relevant URLs)
    page_type = Column(String(100), index=True)
    detected_item_types = Column(ARRAY(item_type_enum))
    content_tags = Column(ARRAY(Text))
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM, index=True)
    has_multiple_items = Column(Boolean, default=False)

    # Content
    raw_markdown = Column(Text)
    content_hash = Column(String(64))

    # Status tracking
    status = Column(Enum(URLStatus), default=URLStatus.DISCOVERED, index=True)
    error_message = Column(Text)

    # Human review
    human_verified = Column(Boolean, default=False)
    human_notes = Column(Text)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at = Column(DateTime(timezone=True))

    # Timestamps
    discovered_at = Column(DateTime(timezone=True))
    last_scraped_at = Column(DateTime(timezone=True))
    last_classified_at = Column(DateTime(timezone=True))

    # Relationships
    source = relationship("Source", back_populates="discovered_urls")
    items = relationship("Item", back_populates="discovered_url")
    verified_by_user = relationship("User", back_populates="verified_urls", foreign_keys=[verified_by])

    __table_args__ = (
        # Unique constraint on source_id + url
        {"schema": None},
    )
