"""Celery task: generate cover letter and auto-apply to a job."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import async_session_factory
from app.models import Application, StoredJob, User

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def apply_to_job(
    self,  # noqa: ARG001
    application_id: str,
    user_id: str,
    pipeline_run_id: str,
) -> dict:
    """Generate a cover letter and submit the application via Playwright."""
    return asyncio.run(_apply_to_job(application_id, user_id, pipeline_run_id))


async def _apply_to_job(
    application_id: str,
    user_id: str,
    pipeline_run_id: str,
) -> dict:
    from app.cover_letter.generator import CoverLetterGenerator, CoverLetterInput
    from app.applicator.engine import AutoApplicator
    from app.config import settings

    # --- Load application + related data ---
    async with async_session_factory() as session:
        app_row = await session.get(Application, application_id)
        if app_row is None:
            raise ValueError(f"Application {application_id} not found")

        app_row.status = "applying"
        await session.flush()

        job = await session.get(StoredJob, app_row.stored_job_id)
        user = await session.get(User, user_id)

        # Load profile for cover letter context
        from app.models import Profile

        result = await session.execute(
            select(Profile).where(Profile.user_id == user_id),
        )
        profile = result.scalar_one_or_none()

    if job is None:
        return await _fail_application(application_id, "StoredJob not found")
    if user is None:
        return await _fail_application(application_id, "User not found")

    profile_dict = {
        "target_roles": profile.target_roles if profile else [],
        "tech_stack": profile.tech_stack if profile else [],
        "experience_level": profile.experience_level if profile else "professional",
    }

    # --- Generate cover letter ---
    cl_input = CoverLetterInput(
        job_title=job.title,
        company=job.company,
        job_description=job.description,
        profile=profile_dict,
        language=job.language,
    )

    generator = CoverLetterGenerator()
    try:
        cover_letter = await generator.generate(cl_input, user_id, job.id)
    except Exception as exc:
        logger.error("Cover letter generation failed for app %s: %s", application_id, exc)
        return await _fail_application(
            application_id,
            f"Cover letter generation failed: {exc}",
            pipeline_run_id,
        )

    # --- Store cover letter ---
    async with async_session_factory() as session:
        app_row = await session.get(Application, application_id)
        if app_row:
            app_row.cover_letter_generated = True
            app_row.cover_letter_text = cover_letter
            await session.commit()

    # --- Run auto-applicator ---
    try:
        async with AutoApplicator(headless=True, timeout=30000) as applicator:
            result = await applicator.apply(
                job_url=job.url,
                cover_letter=cover_letter,
                name=user.name or "Applicant",
                email=user.email,
            )
    except Exception as exc:
        logger.error("Auto-apply failed for app %s: %s", application_id, exc)
        return await _fail_application(
            application_id,
            f"Auto-apply error: {exc}",
            pipeline_run_id,
        )

    # --- Update application status ---
    async with async_session_factory() as session:
        app_row = await session.get(Application, application_id)
        if app_row is None:
            return {"status": "failed", "error": "Application deleted during processing"}

        if result.get("status") == "submitted":
            app_row.status = "submitted"
            app_row.submitted_at = datetime.now(timezone.utc)
        else:
            app_row.status = "failed"
            app_row.error_message = result.get("error", "Unknown error")

        # Update pipeline steps
        from app.models import PipelineRun
        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline:
            step_key = f"apply:{application_id}"
            pipeline.steps = {
                **(pipeline.steps or {}),
                step_key: {
                    "status": result.get("status"),
                    "job_title": job.title,
                    "company": job.company,
                    "error": result.get("error"),
                },
            }
            pipeline.status = "applying"  # keep applying while more apps exist
        await session.commit()

    return {
        "application_id": application_id,
        "status": result.get("status"),
        "error": result.get("error"),
    }


async def _fail_application(
    application_id: str,
    error: str,
    pipeline_run_id: str | None = None,
) -> dict:
    """Mark an application as failed in the database."""
    async with async_session_factory() as session:
        app_row = await session.get(Application, application_id)
        if app_row:
            app_row.status = "failed"
            app_row.error_message = error
        if pipeline_run_id:
            from app.models import PipelineRun
            pipeline = await session.get(PipelineRun, pipeline_run_id)
            if pipeline:
                step_key = f"apply:{application_id}"
                pipeline.steps = {
                    **(pipeline.steps or {}),
                    step_key: {"status": "failed", "error": error},
                }
        await session.commit()
    return {"application_id": application_id, "status": "failed", "error": error}
