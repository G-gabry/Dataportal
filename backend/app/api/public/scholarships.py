from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from uuid import UUID
from math import ceil

from app.core.database import get_db
from app.models.item import Item
from app.models.enums import ItemType, ItemStatus

router = APIRouter()


@router.get("")
def list_scholarships(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    field: Optional[str] = None,
    country: Optional[str] = None,
    eligible_country: Optional[str] = None,
    min_amount: Optional[float] = None,
    covers_tuition: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List published scholarships with filtering"""
    query = db.query(Item).filter(
        Item.item_type == ItemType.SCHOLARSHIP,
        Item.status == ItemStatus.PUBLISHED
    )

    # Apply filters on JSON data
    if field:
        query = query.filter(Item.data["eligible_fields"].astext.ilike(f"%{field}%"))
    if country:
        query = query.filter(Item.data["host_countries"].astext.ilike(f"%{country}%"))
    if eligible_country:
        query = query.filter(Item.data["eligible_countries"].astext.ilike(f"%{eligible_country}%"))
    if covers_tuition is not None:
        query = query.filter(Item.data["covers_tuition"].astext == str(covers_tuition).lower())

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


@router.get("/{scholarship_id}")
def get_scholarship(
    scholarship_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific scholarship"""
    item = db.query(Item).filter(
        Item.id == scholarship_id,
        Item.item_type == ItemType.SCHOLARSHIP,
        Item.status == ItemStatus.PUBLISHED
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Scholarship not found")

    return {
        "id": str(item.id),
        "type": item.item_type.value,
        "data": item.data,
        "custom_fields": item.custom_fields,
        "tags": item.tags,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None
    }


@router.get("/filters/options")
def get_scholarship_filter_options(db: Session = Depends(get_db)):
    """Get available filter options for scholarships"""
    items = db.query(Item).filter(
        Item.item_type == ItemType.SCHOLARSHIP,
        Item.status == ItemStatus.PUBLISHED
    ).all()

    fields = set()
    host_countries = set()
    providers = set()

    for item in items:
        if item.data.get("eligible_fields"):
            for f in item.data["eligible_fields"]:
                fields.add(f)
        if item.data.get("host_countries"):
            for c in item.data["host_countries"]:
                host_countries.add(c)
        if item.data.get("provider"):
            providers.add(item.data["provider"])

    return {
        "fields": sorted(list(fields)),
        "host_countries": sorted(list(host_countries)),
        "providers": sorted(list(providers))
    }
