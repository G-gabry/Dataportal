from sqlalchemy import Column, String, Boolean, Enum, DateTime, ForeignKey, Text, ARRAY, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.models.enums import ItemType, ItemStatus


class Item(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "items"

    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    discovered_url_id = Column(UUID(as_uuid=True), ForeignKey("discovered_urls.id", ondelete="SET NULL"))

    item_type = Column(Enum(ItemType), nullable=False, index=True)

    # The extracted data (schema varies by item_type)
    data = Column(JSONB, nullable=False, default={})

    # Field-level status tracking
    field_status = Column(JSONB, default={})

    # Custom fields added by humans
    custom_fields = Column(JSONB, default={})
    notes = Column(Text)
    admin_notes = Column(Text)
    tags = Column(ARRAY(Text))

    # Quality
    extraction_confidence = Column(Numeric(5, 2))
    status = Column(Enum(ItemStatus), default=ItemStatus.DRAFT, index=True)

    # Human review
    human_edited = Column(Boolean, default=False)
    human_verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at = Column(DateTime(timezone=True))

    # Timestamps
    extracted_at = Column(DateTime(timezone=True))

    # Relationships
    source = relationship("Source", back_populates="items")
    discovered_url = relationship("DiscoveredURL", back_populates="items")
    verified_by_user = relationship("User", back_populates="verified_items", foreign_keys=[verified_by])
