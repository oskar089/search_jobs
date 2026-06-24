"""Celery task: match stored jobs against user profile and create applications."""

import logging
import uuid

from sqlalchemy import select

from app.celery_app import celery_app
from app.config import settings
from app.database import async_session_factory
from app.matching.engine import MatcherEngine
from app.models import Application, PipelineRun, Profile, StoredJob
from app.tasks import run_async

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def match_applications(
    self,  # noqa: ARG001
    user_id: str,
    pipeline_run_id: str,
) -> dict:
    """Score scraped jobs against the user's profile and create applications."""
    return run_async(_match_applications(user_id, pipeline_run_id))


async def _match_applications(
    user_id: str,
    pipeline_run_id: str,
) -> dict:
    engine = MatcherEngine()
    threshold = settings.match_threshold

    async with async_session_factory() as session:
        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline is None:
            raise ValueError(f"PipelineRun {pipeline_run_id} not found")
        pipeline.status = "matching"
        await session.flush()

        # Load profile
        result = await session.execute(
            select(Profile).where(Profile.user_id == user_id),
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            pipeline.status = "failed"
            pipeline.error_step = "match"
            pipeline.error_msg = "User profile not found"
            await session.commit()
            return {"status": "failed", "error": "Profile not found"}

        profile_dict = {
            "target_roles": profile.target_roles,
            "tech_stack": profile.tech_stack,
            "headline": profile.headline or "",
            "summary": profile.summary or "",
            "skills": profile.skills or [],
            "work_experience": profile.work_experience or [],
            "experience_level": profile.experience_level,
            "locations": profile.locations,
            "remote_only": profile.remote_only,
            "languages": profile.languages,
        }

        # Load scraped jobs for this pipeline's portal
        portal_id = pipeline.portal_id
        result = await session.execute(
            select(StoredJob).where(
                StoredJob.portal_id == portal_id,
            ),
        )
        jobs = result.scalars().all()

    # --- Score each job (no session needed) ---
    scored: list[tuple[StoredJob, float, dict]] = []
    for job in jobs:
        job_dict = {
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "location": job.location,
            "language": job.language,
        }
        match = engine.score(profile_dict, job_dict)
        scored.append((job, match.score, match.factors))

    # --- Create Application rows for jobs above threshold ---
    created = 0
    async with async_session_factory() as session:
        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline is None:
            raise ValueError(f"PipelineRun {pipeline_run_id} not found")

        for job, score, factors in scored:
            if score >= threshold:
                app = Application(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    stored_job_id=job.id,
                    pipeline_run_id=pipeline_run_id,
                    status="pending",
                    match_score=score,
                )
                session.add(app)
                created += 1

            # Always log score (even below threshold) for analytics
            logger.info(
                "Match: job=%s score=%.1f threshold=%.1f above=%s",
                job.id, score, threshold, score >= threshold,
            )

        pipeline.steps = {
            **(pipeline.steps or {}),
            "match": {
                "status": "completed",
                "jobs_scored": len(scored),
                "applications_created": created,
                "threshold": threshold,
            },
        }
        await session.commit()

    logger.info(
        "Matched %d jobs — %d applications created (threshold=%.1f)",
        len(scored), created, threshold,
    )
    return {"status": "completed", "jobs_scored": len(scored), "applications_created": created}
