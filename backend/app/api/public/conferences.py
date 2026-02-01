from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from uuid import UUID
from math import ceil
from datetime import date

from app.core.database import get_db
from app.models.item import Item
from app.models.enums import ItemType, ItemStatus

router = APIRouter()


@router.get("")
def list_conferences(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    field: Optional[str] = None,
    country: Optional[str] = None,
    is_virtual: Optional[bool] = None,
    upcoming_only: bool = True,
    db: Session = Depends(get_db)
):
    """List published conferences with filtering"""
    query = db.query(Item).filter(
        Item.item_type == ItemType.CONFERENCE,
        Item.status == ItemStatus.PUBLISHED
    )

    # Apply filters on JSON data
    if field:
        query = query.filter(Item.data["field"].astext.ilike(f"%{field}%"))
    if country:
        query = query.filter(Item.data["country"].astext.ilike(f"%{country}%"))
    if is_virtual is not None:
        query = query.filter(Item.data["is_virtual"].astext == str(is_virtual).lower())

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(desc(Item.updated_at)).offset(offset).limit(page_size).all()

    return {
        "items": [
            {
                "id": str(item.id),
                "type": item.item_type.value,
                "data": item.data,
                "tags": item.tags,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total > 0 else 1
    }


@router.get("/{conference_id}")
def get_conference(
    conference_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific conference"""
    item = db.query(Item).filter(
        Item.id == conference_id,
        Item.item_type == ItemType.CONFERENCE,
        Item.status == ItemStatus.PUBLISHED
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Conference not found")

    return {
        "id": str(item.id),
        "type": item.item_type.value,
        "data": item.data,
        "custom_fields": item.custom_fields,
        "tags": item.tags,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None
    }


@router.get("/filters/options")
def get_conference_filter_options(db: Session = Depends(get_db)):
    """Get available filter options for conferences"""
    items = db.query(Item).filter(
        Item.item_type == ItemType.CONFERENCE,
        Item.status == ItemStatus.PUBLISHED
    ).all()

    fields = set()
    countries = set()
    topics = set()

    for item in items:
        if item.data.get("field"):
            fields.add(item.data["field"])
        if item.data.get("country"):
            countries.add(item.data["country"])
        if item.data.get("topics"):
            for t in item.data["topics"]:
                topics.add(t)

    return {
        "fields": sorted(list(fields)),
        "countries": sorted(list(countries)),
        "topics": sorted(list(topics))
    }
