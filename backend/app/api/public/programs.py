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
def list_programs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    field: Optional[str] = None,
    country: Optional[str] = None,
    degree_type: Optional[str] = None,
    min_gpa: Optional[float] = None,
    max_tuition: Optional[float] = None,
    has_funding: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List published programs with filtering"""
    query = db.query(Item).filter(
        Item.item_type == ItemType.PROGRAM,
        Item.status == ItemStatus.PUBLISHED
    )

    # Apply filters on JSON data
    if field:
        query = query.filter(Item.data["field"].astext.ilike(f"%{field}%"))
    if country:
        query = query.filter(Item.data["country"].astext.ilike(f"%{country}%"))
    if degree_type:
        query = query.filter(Item.data["degree_type"].astext == degree_type)
    if min_gpa is not None:
        query = query.filter(Item.data["gpa_requirement"].astext.cast(db.bind.dialect.type_descriptor(db.Float)) <= min_gpa)
    if max_tuition is not None:
        query = query.filter(Item.data["tuition_per_year_usd"].astext.cast(db.bind.dialect.type_descriptor(db.Float)) <= max_tuition)
    if has_funding is not None:
        query = query.filter(Item.data["has_funding"].astext == str(has_funding).lower())

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


@router.get("/{program_id}")
def get_program(
    program_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific program"""
    item = db.query(Item).filter(
        Item.id == program_id,
        Item.item_type == ItemType.PROGRAM,
        Item.status == ItemStatus.PUBLISHED
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Program not found")

    return {
        "id": str(item.id),
        "type": item.item_type.value,
        "data": item.data,
        "custom_fields": item.custom_fields,
        "tags": item.tags,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None
    }


@router.get("/filters/options")
def get_program_filter_options(db: Session = Depends(get_db)):
    """Get available filter options for programs"""
    items = db.query(Item).filter(
        Item.item_type == ItemType.PROGRAM,
        Item.status == ItemStatus.PUBLISHED
    ).all()

    fields = set()
    countries = set()
    degree_types = set()

    for item in items:
        if item.data.get("field"):
            fields.add(item.data["field"])
        if item.data.get("country"):
            countries.add(item.data["country"])
        if item.data.get("degree_type"):
            degree_types.add(item.data["degree_type"])

    return {
        "fields": sorted(list(fields)),
        "countries": sorted(list(countries)),
        "degree_types": sorted(list(degree_types))
    }
