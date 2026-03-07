from sqlalchemy import Column, String, Boolean, Integer, Enum, DateTime, ARRAY, Text
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.models.enums import SourceType, ItemType

# Create PostgreSQL ENUM type that matches the database
item_type_enum = ENUM('PROGRAM', 'SCHOLARSHIP', 'CONFERENCE', 'EXCHANGE', name='item_type', create_type=False)


class Source(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sources"

    name = Column(String(255), nullable=False)
    type = Column(Enum(SourceType), nullable=False, index=True)
    base_url = Column(String(500), nullable=False)
    target_item_types = Column(ARRAY(item_type_enum), nullable=False)

    # Scraping config
    scrape_frequency = Column(String(50), default="MONTHLY")
    is_important = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)

    # URL filtering patterns and crawl logic
    sitemap_url = Column(String(500), nullable=True)
    dfs_depth = Column(Integer, default=1)
    max_urls_per_run = Column(Integer, nullable=True)
    include_patterns = Column(ARRAY(Text), default=[])
    exclude_patterns = Column(ARRAY(Text), default=[])

    # Status
    last_scraped_at = Column(DateTime(timezone=True))
    urls_discovered_count = Column(Integer, default=0)
    items_extracted_count = Column(Integer, default=0)

    # Flexible extra data
    extra_data = Column(JSONB, default={})
    notes = Column(Text)

    # Relationships
    discovered_urls = relationship("DiscoveredURL", back_populates="source", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="source", cascade="all, delete-orphan")
    scrape_jobs = relationship("ScrapeJob", back_populates="source", cascade="all, delete-orphan")
