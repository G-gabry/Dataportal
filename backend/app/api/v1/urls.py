from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from math import ceil

from app.core.database import get_db
from app.models.discovered_url import DiscoveredURL
from app.models.user import User
from app.models.enums import URLStatus, RelevanceStatus, PriorityLevel, ItemType
from app.schemas.discovered_url import DiscoveredURLResponse, DiscoveredURLUpdate, DiscoveredURLListResponse
from app.schemas.common import MessageResponse
from app.api.deps import get_current_user, get_editor_user

router = APIRouter()


@router.get("", response_model=DiscoveredURLListResponse)
def list_urls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_id: Optional[UUID] = None,
    status: Optional[URLStatus] = None,
    relevance: Optional[RelevanceStatus] = None,
    priority: Optional[PriorityLevel] = None,
    page_type: Optional[str] = None,
    human_verified: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List discovered URLs with filtering and pagination"""
    query = db.query(DiscoveredURL)

    # Apply filters
    if source_id:
        query = query.filter(DiscoveredURL.source_id == source_id)
    if status:
        query = query.filter(DiscoveredURL.status == status)
    if relevance:
        query = query.filter(DiscoveredURL.relevance == relevance)
    if priority:
        query = query.filter(DiscoveredURL.priority == priority)
    if page_type:
        query = query.filter(DiscoveredURL.page_type == page_type)
    if human_verified is not None:
        query = query.filter(DiscoveredURL.human_verified == human_verified)
    if search:
        query = query.filter(DiscoveredURL.url.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    urls = query.order_by(desc(DiscoveredURL.discovered_at)).offset(offset).limit(page_size).all()

    return DiscoveredURLListResponse(
        items=[DiscoveredURLResponse.model_validate(u) for u in urls],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 1
    )


@router.get("/{url_id}", response_model=DiscoveredURLResponse)
def get_url(
    url_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific discovered URL by ID"""
    url = db.query(DiscoveredURL).filter(DiscoveredURL.id == url_id).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    return DiscoveredURLResponse.model_validate(url)


@router.put("/{url_id}", response_model=DiscoveredURLResponse)
def update_url(
    url_id: UUID,
    url_data: DiscoveredURLUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Update a discovered URL (human review)"""
    url = db.query(DiscoveredURL).filter(DiscoveredURL.id == url_id).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    # Update only provided fields
    update_data = url_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(url, key, value)

    # Mark as human verified if relevant fields are updated
    if url_data.human_verified:
        url.human_verified = True
        url.verified_by = current_user.id
        url.verified_at = datetime.utcnow()

    db.commit()
    db.refresh(url)
    return DiscoveredURLResponse.model_validate(url)


@router.delete("/{url_id}", response_model=MessageResponse)
def delete_url(
    url_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Delete a discovered URL"""
    url = db.query(DiscoveredURL).filter(DiscoveredURL.id == url_id).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    db.delete(url)
    db.commit()
    return MessageResponse(message="URL deleted successfully")


@router.post("/{url_id}/verify", response_model=DiscoveredURLResponse)
def verify_url(
    url_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Mark a URL as human verified"""
    url = db.query(DiscoveredURL).filter(DiscoveredURL.id == url_id).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    url.human_verified = True
    url.verified_by = current_user.id
    url.verified_at = datetime.utcnow()

    db.commit()
    db.refresh(url)
    return DiscoveredURLResponse.model_validate(url)


@router.get("/stats/summary")
def get_url_stats(
    source_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get URL statistics summary"""
    query = db.query(DiscoveredURL)
    if source_id:
        query = query.filter(DiscoveredURL.source_id == source_id)

    total = query.count()
    relevant = query.filter(DiscoveredURL.relevance == RelevanceStatus.RELEVANT).count()
    not_relevant = query.filter(DiscoveredURL.relevance == RelevanceStatus.NOT_RELEVANT).count()
    pending = query.filter(DiscoveredURL.relevance == RelevanceStatus.PENDING).count()
    verified = query.filter(DiscoveredURL.human_verified == True).count()

    # Status breakdown
    status_counts = {}
    for s in URLStatus:
        status_counts[s.value] = query.filter(DiscoveredURL.status == s).count()

    # Priority breakdown
    priority_counts = {}
    for p in PriorityLevel:
        priority_counts[p.value] = query.filter(DiscoveredURL.priority == p).count()

    return {
        "total": total,
        "relevance": {
            "relevant": relevant,
            "not_relevant": not_relevant,
            "pending": pending
        },
        "human_verified": verified,
        "status": status_counts,
        "priority": priority_counts
    }
