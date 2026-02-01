from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import Optional
from uuid import UUID
from math import ceil

from app.core.database import get_db
from app.models.scrape_job import ScrapeJob
from app.models.ai_log import AILog
from app.models.user import User
from app.models.enums import JobStatus
from app.schemas.job import ScrapeJobResponse, ScrapeJobListResponse
from app.schemas.common import MessageResponse
from app.api.deps import get_current_user, get_editor_user

router = APIRouter()


@router.get("", response_model=ScrapeJobListResponse)
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_id: Optional[UUID] = None,
    status: Optional[JobStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List scrape jobs with filtering and pagination"""
    query = db.query(ScrapeJob).options(joinedload(ScrapeJob.source))

    # Apply filters
    if source_id:
        query = query.filter(ScrapeJob.source_id == source_id)
    if status:
        query = query.filter(ScrapeJob.status == status)

    # Get total count (without joinedload for efficiency)
    count_query = db.query(ScrapeJob)
    if source_id:
        count_query = count_query.filter(ScrapeJob.source_id == source_id)
    if status:
        count_query = count_query.filter(ScrapeJob.status == status)
    total = count_query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(ScrapeJob.created_at)).offset(offset).limit(page_size).all()

    return ScrapeJobListResponse(
        items=[ScrapeJobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 1
    )


@router.get("/{job_id}", response_model=ScrapeJobResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific job by ID"""
    job = db.query(ScrapeJob).options(joinedload(ScrapeJob.source)).filter(ScrapeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ScrapeJobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=MessageResponse)
def cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Cancel a running job"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        raise HTTPException(status_code=400, detail="Job is not cancellable")

    job.status = JobStatus.CANCELLED
    db.commit()

    return MessageResponse(message="Job cancelled successfully")


@router.get("/{job_id}/logs")
def get_job_logs(
    job_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI logs for a specific job"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    query = db.query(AILog).filter(AILog.job_id == job_id)
    total = query.count()

    offset = (page - 1) * page_size
    logs = query.order_by(desc(AILog.created_at)).offset(offset).limit(page_size).all()

    return {
        "items": [
            {
                "id": str(log.id),
                "task_type": log.task_type,
                "model_used": log.model_used,
                "provider": log.provider,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "cost_usd": float(log.cost_usd) if log.cost_usd else 0,
                "latency_ms": log.latency_ms,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total > 0 else 1
    }


@router.get("/stats/summary")
def get_job_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get job statistics summary"""
    from sqlalchemy import func

    total = db.query(ScrapeJob).count()

    # Status breakdown
    status_counts = {}
    for s in JobStatus:
        status_counts[s.value] = db.query(ScrapeJob).filter(ScrapeJob.status == s).count()

    # Cost summary
    cost_stats = db.query(
        func.sum(ScrapeJob.ai_cost_usd).label("total_cost"),
        func.sum(ScrapeJob.ai_tokens_used).label("total_tokens"),
        func.sum(ScrapeJob.firecrawl_calls).label("total_firecrawl_calls"),
        func.sum(ScrapeJob.items_extracted).label("total_items_extracted")
    ).first()

    return {
        "total_jobs": total,
        "by_status": status_counts,
        "total_cost_usd": float(cost_stats.total_cost) if cost_stats.total_cost else 0,
        "total_tokens": cost_stats.total_tokens or 0,
        "total_firecrawl_calls": cost_stats.total_firecrawl_calls or 0,
        "total_items_extracted": cost_stats.total_items_extracted or 0
    }
