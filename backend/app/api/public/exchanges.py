"""
Public API for Exchanges - Production Ready

Returns simplified exchange data: name, url, country, summary
"""
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


def serialize_exchange(item: Item) -> dict:
    """Serialize exchange item for API response"""
    return {
        "id": str(item.id),
        "name": item.data.get("name"),
        "url": item.data.get("url"),
        "country": item.data.get("country"),
        "summary": item.data.get("summary"),
        "source_id": str(item.source_id) if item.source_id else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.get("")
def list_exchanges(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    country: Optional[str] = Query(None, description="Filter by country"),
    search: Optional[str] = Query(None, description="Search in name and summary"),
    db: Session = Depends(get_db)
):
    """
    List all published exchange programs.

    Returns paginated list with simplified fields: name, url, country, summary.
    """
    query = db.query(Item).filter(
        Item.item_type == ItemType.EXCHANGE,
        Item.status == ItemStatus.PUBLISHED
    )

    # Apply filters
    if country:
        query = query.filter(Item.data["country"].astext.ilike(f"%{country}%"))

    if search:
        query = query.filter(
            (Item.data["name"].astext.ilike(f"%{search}%")) |
            (Item.data["summary"].astext.ilike(f"%{search}%"))
        )

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(desc(Item.updated_at)).offset(offset).limit(page_size).all()

    return {
        "items": [serialize_exchange(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total > 0 else 1,
    }


@router.get("/countries")
def get_exchange_countries(db: Session = Depends(get_db)):
    """Get list of all countries with exchanges"""
    items = db.query(Item).filter(
        Item.item_type == ItemType.EXCHANGE,
        Item.status == ItemStatus.PUBLISHED
    ).all()

    countries = set()
    for item in items:
        country = item.data.get("country")
        if country:
            countries.add(country)

    return {"countries": sorted(list(countries))}


@router.get("/{exchange_id}")
def get_exchange(exchange_id: UUID, db: Session = Depends(get_db)):
    """Get a specific exchange program by ID"""
    item = db.query(Item).filter(
        Item.id == exchange_id,
        Item.item_type == ItemType.EXCHANGE,
        Item.status == ItemStatus.PUBLISHED
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Exchange program not found")

    return serialize_exchange(item)
