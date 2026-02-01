from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.models.enums import UserRole


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.EDITOR)
    is_active = Column(Boolean, default=True)

    # Relationships
    verified_urls = relationship("DiscoveredURL", back_populates="verified_by_user", foreign_keys="DiscoveredURL.verified_by")
    verified_items = relationship("Item", back_populates="verified_by_user", foreign_keys="Item.verified_by")
    created_jobs = relationship("ScrapeJob", back_populates="created_by_user")
