from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, String
from typing import Optional, List
from math import ceil

from app.core.database import get_db
from app.models.item import Item
from app.models.enums import ItemType, ItemStatus

router = APIRouter()


@router.get("")
def search_items(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_types: Optional[List[ItemType]] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Search across all published items.
    Searches in the JSON data field.
    """
    query = db.query(Item).filter(
        Item.status == ItemStatus.PUBLISHED
    )

    # Filter by item types if specified
    if item_types:
        query = query.filter(Item.item_type.in_(item_types))

    # Search in JSON data (simple text search)
    # For production, consider using PostgreSQL full-text search or Elasticsearch
    query = query.filter(
        func.cast(Item.data, String).ilike(f"%{q}%")
    )

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(desc(Item.updated_at)).offset(offset).limit(page_size).all()

    return {
        "query": q,
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


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get overall statistics for the data portal"""
    stats = {}

    for item_type in ItemType:
        count = db.query(Item).filter(
            Item.item_type == item_type,
            Item.status == ItemStatus.PUBLISHED
        ).count()
        stats[item_type.value.lower() + "s"] = count

    stats["total"] = sum(stats.values())

    return stats
