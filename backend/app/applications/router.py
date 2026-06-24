"""Applications endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.router import get_current_user_id
from app.database import get_session
from app.models import Application, Portal, StoredJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
async def list_applications(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
    status_filter: str | None = None,
):
    """Return the current user's applications, newest first.

    Optionally filter by status (pending, applying, submitted, failed).
    """
    query = (
        select(Application)
        .options(
            joinedload(Application.stored_job),
        )
        .where(Application.user_id == user_id)
    )

    if status_filter:
        query = query.where(Application.status == status_filter)

    query = query.order_by(Application.created_at.desc()).limit(limit)

    result = await session.execute(query)
    applications = result.unique().scalars().all()

    # Batch-load portal names
    portal_ids = {app.stored_job.portal_id for app in applications if app.stored_job}
    if portal_ids:
        portals_result = await session.execute(
            select(Portal).where(Portal.id.in_(portal_ids)),
        )
        portal_map = {p.id: p.name for p in portals_result.scalars().all()}
    else:
        portal_map = {}

    return [
        {
            "id": app.id,
            "stored_job_id": app.stored_job_id,
            "pipeline_run_id": app.pipeline_run_id,
            "status": app.status,
            "match_score": app.match_score,
            "company": app.stored_job.company if app.stored_job else "Unknown",
            "job_title": app.stored_job.title if app.stored_job else "Unknown",
            "job_url": app.stored_job.url if app.stored_job else None,
            "portal_name": portal_map.get(app.stored_job.portal_id, "Unknown") if app.stored_job else "Unknown",
            "cover_letter_generated": app.cover_letter_generated,
            "cover_letter_text": app.cover_letter_text,
            "error_message": app.error_message,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "created_at": app.created_at.isoformat(),
        }
        for app in applications
    ]


@router.get("/{application_id}")
async def get_application(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Return a single application with full detail."""
    result = await session.execute(
        select(Application)
        .options(joinedload(Application.stored_job))
        .where(Application.id == application_id, Application.user_id == user_id),
    )
    app = result.unique().scalar_one_or_none()

    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    portal_name = "Unknown"
    if app.stored_job:
        portal_result = await session.execute(
            select(Portal.name).where(Portal.id == app.stored_job.portal_id),
        )
        row = portal_result.one_or_none()
        if row:
            portal_name = row[0]

    return {
        "id": app.id,
        "stored_job_id": app.stored_job_id,
        "pipeline_run_id": app.pipeline_run_id,
        "status": app.status,
        "match_score": app.match_score,
        "company": app.stored_job.company if app.stored_job else "Unknown",
        "job_title": app.stored_job.title if app.stored_job else "Unknown",
        "job_description": app.stored_job.description if app.stored_job else None,
        "job_url": app.stored_job.url if app.stored_job else None,
        "job_location": app.stored_job.location if app.stored_job else None,
        "salary_range": app.stored_job.salary_range if app.stored_job else None,
        "portal_name": portal_name,
        "cover_letter_generated": app.cover_letter_generated,
        "cover_letter_text": app.cover_letter_text,
        "error_message": app.error_message,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
    }
