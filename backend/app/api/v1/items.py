from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from math import ceil

from app.core.database import get_db
from app.models.item import Item
from app.models.source import Source
from app.models.user import User
from app.models.enums import ItemType, ItemStatus
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse
from app.schemas.common import MessageResponse
from app.api.deps import get_current_user, get_editor_user

router = APIRouter()


@router.get("", response_model=ItemListResponse)
def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_id: Optional[UUID] = None,
    item_type: Optional[ItemType] = None,
    status: Optional[ItemStatus] = None,
    human_verified: Optional[bool] = None,
    needs_review: bool = False,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List items with filtering and pagination"""
    query = db.query(Item)

    # Apply filters
    if source_id:
        query = query.filter(Item.source_id == source_id)
    if item_type:
        query = query.filter(Item.item_type == item_type)
    if status:
        query = query.filter(Item.status == status)
    if human_verified is not None:
        query = query.filter(Item.human_verified == human_verified)
    if needs_review:
        query = query.filter(Item.status == ItemStatus.NEEDS_REVIEW)
    if search:
        # Search in JSON data
        query = query.filter(
            func.cast(Item.data, String).ilike(f"%{search}%")
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.order_by(desc(Item.created_at)).offset(offset).limit(page_size).all()

    return ItemListResponse(
        items=[ItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 1
    )


@router.get("/review-queue", response_model=ItemListResponse)
def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_type: Optional[ItemType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get items that need review"""
    query = db.query(Item).filter(
        (Item.status == ItemStatus.NEEDS_REVIEW) |
        (Item.status == ItemStatus.DRAFT) |
        ((Item.human_verified == False) & (Item.status == ItemStatus.VERIFIED))
    )

    if item_type:
        query = query.filter(Item.item_type == item_type)

    # Order by extraction confidence (lowest first)
    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Item.extraction_confidence.asc().nullsfirst()).offset(offset).limit(page_size).all()

    return ItemListResponse(
        items=[ItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 1
    )


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific item by ID"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse.model_validate(item)


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Create a new item manually"""
    # Verify source exists
    source = db.query(Source).filter(Source.id == item_data.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    item = Item(
        source_id=item_data.source_id,
        discovered_url_id=item_data.discovered_url_id,
        item_type=item_data.item_type,
        data=item_data.data,
        custom_fields=item_data.custom_fields,
        notes=item_data.notes,
        admin_notes=item_data.admin_notes,
        tags=item_data.tags,
        status=ItemStatus.DRAFT,
        human_edited=True  # Manually created
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Update source item count
    source.items_extracted_count = db.query(Item).filter(Item.source_id == source.id).count()
    db.commit()

    return ItemResponse.model_validate(item)


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: UUID,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Update an item"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Update only provided fields
    update_data = item_data.model_dump(exclude_unset=True)

    # Handle data update (merge with existing)
    if "data" in update_data and update_data["data"]:
        merged_data = {**item.data, **update_data["data"]}
        item.data = merged_data
        del update_data["data"]

    # Handle custom_fields update (merge with existing)
    if "custom_fields" in update_data and update_data["custom_fields"]:
        merged_custom = {**item.custom_fields, **update_data["custom_fields"]}
        item.custom_fields = merged_custom
        del update_data["custom_fields"]

    for key, value in update_data.items():
        setattr(item, key, value)

    # Mark as human edited
    item.human_edited = True

    # Handle verification
    if item_data.human_verified:
        item.human_verified = True
        item.verified_by = current_user.id
        item.verified_at = datetime.utcnow()

    db.commit()
    db.refresh(item)
    return ItemResponse.model_validate(item)


@router.delete("/{item_id}", response_model=MessageResponse)
def delete_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Delete an item"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    source_id = item.source_id
    db.delete(item)
    db.commit()

    # Update source item count
    source = db.query(Source).filter(Source.id == source_id).first()
    if source:
        source.items_extracted_count = db.query(Item).filter(Item.source_id == source_id).count()
        db.commit()

    return MessageResponse(message="Item deleted successfully")


@router.post("/{item_id}/verify", response_model=ItemResponse)
def verify_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Mark an item as verified"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.human_verified = True
    item.status = ItemStatus.VERIFIED
    item.verified_by = current_user.id
    item.verified_at = datetime.utcnow()

    db.commit()
    db.refresh(item)
    return ItemResponse.model_validate(item)


@router.post("/{item_id}/publish", response_model=ItemResponse)
def publish_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Publish an item (make it visible in public API)"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.status = ItemStatus.PUBLISHED
    db.commit()
    db.refresh(item)
    return ItemResponse.model_validate(item)


@router.get("/stats/summary")
def get_item_stats(
    source_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get item statistics summary"""
    query = db.query(Item)
    if source_id:
        query = query.filter(Item.source_id == source_id)

    total = query.count()
    verified = query.filter(Item.human_verified == True).count()
    edited = query.filter(Item.human_edited == True).count()

    # Type breakdown
    type_counts = {}
    for t in ItemType:
        type_counts[t.value] = query.filter(Item.item_type == t).count()

    # Status breakdown
    status_counts = {}
    for s in ItemStatus:
        status_counts[s.value] = query.filter(Item.status == s).count()

    return {
        "total": total,
        "human_verified": verified,
        "human_edited": edited,
        "by_type": type_counts,
        "by_status": status_counts
    }


# Need to import String for the search filter
from sqlalchemy import String
