"""Stored jobs endpoints."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user_id
from app.database import get_session
from app.models import Application, Portal, StoredJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/")
async def list_stored_jobs(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
):
    """Return stored jobs visible to the current user (public + owned portals)."""
    result = await session.execute(
        select(StoredJob)
        .join(Portal, StoredJob.portal_id == Portal.id)
        .where(
            (Portal.user_id == user_id) | (Portal.user_id.is_(None)),
        )
        .order_by(StoredJob.scraped_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()

    # Batch-load portal names
    portal_ids = {j.portal_id for j in jobs}
    portals_result = await session.execute(
        select(Portal).where(Portal.id.in_(portal_ids))
    )
    portal_map = {p.id: p for p in portals_result.scalars().all()}

    # Batch-load match scores from Application table
    job_ids = [j.id for j in jobs]
    apps_result = await session.execute(
        select(Application.stored_job_id, Application.match_score).where(
            Application.stored_job_id.in_(job_ids),
            Application.user_id == user_id,
        )
    )
    match_scores = {row.stored_job_id: row.match_score for row in apps_result}

    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "url": j.url,
            "salary_range": j.salary_range,
            "posted_at": j.posted_at.isoformat() if j.posted_at else None,
            "scraped_at": j.scraped_at.isoformat(),
            "language": j.language,
            "portal_name": portal_map[j.portal_id].name if j.portal_id in portal_map else "Unknown",
            "match_score": match_scores.get(j.id),
        }
        for j in jobs
    ]


@router.delete("/")
async def clear_stored_jobs(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete all stored jobs (and their applications) for this user's portals."""
    # Get portal IDs visible to this user (own portals + public portals)
    result = await session.execute(
        select(Portal.id).where(
            (Portal.user_id == user_id) | (Portal.user_id.is_(None)),
        ),
    )
    portal_ids = [row[0] for row in result]

    if not portal_ids:
        return {"deleted": 0}

    # Get job IDs for those portals
    result = await session.execute(
        select(StoredJob.id).where(StoredJob.portal_id.in_(portal_ids))
    )
    job_ids = [row[0] for row in result]

    deleted = len(job_ids)
    if not job_ids:
        return {"deleted": 0}

    # Delete applications referencing those jobs first (FK constraint)
    await session.execute(
        sa_delete(Application).where(Application.stored_job_id.in_(job_ids))
    )
    # Delete the stored jobs
    await session.execute(
        sa_delete(StoredJob).where(StoredJob.portal_id.in_(portal_ids))
    )
    await session.commit()

    logger.info("Cleared %d stored jobs for user %s", deleted, user_id)
    return {"deleted": deleted}
