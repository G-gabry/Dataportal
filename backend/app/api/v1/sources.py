from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from uuid import UUID
from math import ceil

from app.core.database import get_db
from app.models.source import Source
from app.models.user import User
from app.models.enums import SourceType, ItemType
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse, SourceListResponse
from app.schemas.common import MessageResponse
from app.api.deps import get_current_user, get_editor_user
from app.tasks.scrape_task import run_scrape_job

router = APIRouter()


@router.get("", response_model=SourceListResponse)
def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[SourceType] = None,
    is_active: Optional[bool] = None,
    is_important: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sources with filtering and pagination"""
    query = db.query(Source)

    # Apply filters
    if type:
        query = query.filter(Source.type == type)
    if is_active is not None:
        query = query.filter(Source.is_active == is_active)
    if is_important is not None:
        query = query.filter(Source.is_important == is_important)
    if search:
        query = query.filter(Source.name.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    sources = query.order_by(desc(Source.is_important), Source.name).offset(offset).limit(page_size).all()

    return SourceListResponse(
        items=[SourceResponse.model_validate(s) for s in sources],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 1
    )


@router.get("/{source_id}", response_model=SourceResponse)
def get_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific source by ID"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse.model_validate(source)


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    source_data: SourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Create a new source"""
    source = Source(
        name=source_data.name,
        type=source_data.type,
        base_url=source_data.base_url,
        target_item_types=source_data.target_item_types,
        scrape_frequency=source_data.scrape_frequency,
        is_important=source_data.is_important,
        is_active=source_data.is_active,
        include_patterns=source_data.include_patterns,
        exclude_patterns=source_data.exclude_patterns,
        extra_data=source_data.extra_data,
        notes=source_data.notes
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return SourceResponse.model_validate(source)


@router.put("/{source_id}", response_model=SourceResponse)
def update_source(
    source_id: UUID,
    source_data: SourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Update a source"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Update only provided fields
    update_data = source_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)

    db.commit()
    db.refresh(source)
    return SourceResponse.model_validate(source)


@router.delete("/{source_id}", response_model=MessageResponse)
def delete_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Delete a source"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    db.delete(source)
    db.commit()
    return MessageResponse(message=f"Source '{source.name}' deleted successfully")


@router.post("/{source_id}/scrape", response_model=MessageResponse)
def trigger_scrape(
    source_id: UUID,
    job_type: str = "FULL_SCRAPE",
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Trigger a scrape job for a source"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if not source.is_active:
        raise HTTPException(status_code=400, detail="Source is not active")

    # Start background job
    background_tasks.add_task(run_scrape_job, source_id, job_type, current_user.id)

    return MessageResponse(message=f"Scrape job started for '{source.name}'")
