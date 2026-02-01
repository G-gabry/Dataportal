from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from uuid import UUID
from math import ceil

from app.core.database import get_db
from app.models.item import Item
from app.models.enums import ItemType, ItemStatus

router = APIRouter()


@router.get("")
def list_exchanges(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    host_country: Optional[str] = None,
    program_type: Optional[str] = None,
    has_stipend: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List published exchange programs with filtering"""
    query = db.query(Item).filter(
        Item.item_type == ItemType.EXCHANGE,
        Item.status == ItemStatus.PUBLISHED
    )

    # Apply filters on JSON data
    if host_country:
        query = query.filter(Item.data["host_country"].astext.ilike(f"%{host_country}%"))
    if program_type:
        query = query.filter(Item.data["program_type"].astext == program_type)

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


@router.get("/{exchange_id}")
def get_exchange(
    exchange_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific exchange program"""
    item = db.query(Item).filter(
        Item.id == exchange_id,
        Item.item_type == ItemType.EXCHANGE,
        Item.status == ItemStatus.PUBLISHED
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Exchange program not found")

    return {
        "id": str(item.id),
        "type": item.item_type.value,
        "data": item.data,
        "custom_fields": item.custom_fields,
        "tags": item.tags,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None
    }


@router.get("/filters/options")
def get_exchange_filter_options(db: Session = Depends(get_db)):
    """Get available filter options for exchange programs"""
    items = db.query(Item).filter(
        Item.item_type == ItemType.EXCHANGE,
        Item.status == ItemStatus.PUBLISHED
    ).all()

    host_countries = set()
    host_universities = set()
    program_types = set()

    for item in items:
        if item.data.get("host_country"):
            host_countries.add(item.data["host_country"])
        if item.data.get("host_university"):
            host_universities.add(item.data["host_university"])
        if item.data.get("program_type"):
            program_types.add(item.data["program_type"])

    return {
        "host_countries": sorted(list(host_countries)),
        "host_universities": sorted(list(host_universities)),
        "program_types": sorted(list(program_types))
    }
