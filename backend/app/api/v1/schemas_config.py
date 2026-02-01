from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.item_schema import ItemSchema
from app.models.user import User
from app.models.enums import ItemType
from app.schemas.setting import ItemSchemaResponse, ItemSchemaUpdate
from app.api.deps import get_current_user, get_admin_user

router = APIRouter()


@router.get("", response_model=List[ItemSchemaResponse])
def list_schemas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all item schemas"""
    schemas = db.query(ItemSchema).filter(ItemSchema.is_active == True).all()
    return [ItemSchemaResponse.model_validate(s) for s in schemas]


@router.get("/{item_type}", response_model=ItemSchemaResponse)
def get_schema(
    item_type: ItemType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get schema for a specific item type"""
    schema = db.query(ItemSchema).filter(
        ItemSchema.item_type == item_type,
        ItemSchema.is_active == True
    ).first()
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema not found for {item_type}")
    return ItemSchemaResponse.model_validate(schema)


@router.put("/{item_type}", response_model=ItemSchemaResponse)
def update_schema(
    item_type: ItemType,
    schema_data: ItemSchemaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Update schema for a specific item type (admin only)"""
    schema = db.query(ItemSchema).filter(
        ItemSchema.item_type == item_type,
        ItemSchema.is_active == True
    ).first()
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema not found for {item_type}")

    # Update only provided fields
    update_data = schema_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(schema, key, value)

    # Increment version
    schema.version += 1

    db.commit()
    db.refresh(schema)
    return ItemSchemaResponse.model_validate(schema)


@router.get("/{item_type}/fields")
def get_schema_fields(
    item_type: ItemType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get just the field definitions for a specific item type"""
    schema = db.query(ItemSchema).filter(
        ItemSchema.item_type == item_type,
        ItemSchema.is_active == True
    ).first()
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema not found for {item_type}")

    return {
        "item_type": item_type,
        "fields": schema.schema_json.get("fields", {}),
        "version": schema.version
    }
