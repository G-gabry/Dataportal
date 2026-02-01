from sqlalchemy import Column, String, Boolean, Integer, Enum, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.models.enums import ItemType


class ItemSchema(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "item_schemas"

    item_type = Column(Enum(ItemType), unique=True, nullable=False)

    # Schema definition
    schema_json = Column(JSONB, nullable=False)

    # AI prompts
    classification_prompt = Column(Text)
    extraction_prompt = Column(Text)

    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
