"""PipelineRun state machine: orchestrates scrape → match → apply → notify."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import async_session_factory
from app.models import Application, PipelineRun
from app.tasks import run_async

logger = logging.getLogger(__name__)


@celery_app.task
def run_pipeline(pipeline_run_id: str) -> dict:
    """Orchestrate the full worker pipeline for a PipelineRun."""
    return run_async(_run_pipeline(pipeline_run_id))


async def _is_cancelled(pipeline_run_id: str) -> bool:
    """Check if the pipeline run was cancelled by the user."""
    async with async_session_factory() as session:
        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline is None:
            return True
        return pipeline.status == "cancelled"


async def _run_pipeline(pipeline_run_id: str) -> dict:
    # --- Load pipeline ---
    async with async_session_factory() as session:
        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline is None:
            raise ValueError(f"PipelineRun {pipeline_run_id} not found")
        portal_id = pipeline.portal_id
        user_id = pipeline.user_id

    logger.info(
        "Starting pipeline %s (portal=%s, user=%s)",
        pipeline_run_id, portal_id, user_id,
    )

    # Check if cancelled before starting
    if await _is_cancelled(pipeline_run_id):
        logger.info("Pipeline %s was cancelled before starting", pipeline_run_id)
        return {"status": "cancelled"}

    # --- Step 1: Scrape ---
    logger.info("Pipeline %s — step: scrape", pipeline_run_id)
    from app.tasks.scrape import _scrape_portal

    scrape_result = await _scrape_portal(portal_id, user_id, pipeline_run_id)
    if scrape_result.get("status") == "failed":
        return await _set_pipeline_failed(pipeline_run_id, "scrape", scrape_result.get("error", ""))
    if await _is_cancelled(pipeline_run_id):
        return {"status": "cancelled"}

    jobs_found = scrape_result.get("jobs_found", 0)
    if jobs_found == 0:
        logger.info("Pipeline %s — no jobs found, marking completed", pipeline_run_id)
        return await _set_pipeline_completed(pipeline_run_id)

    # --- Step 2: Match ---
    logger.info("Pipeline %s — step: match", pipeline_run_id)
    from app.tasks.match import _match_applications

    match_result = await _match_applications(user_id, pipeline_run_id)
    if match_result.get("status") == "failed":
        return await _set_pipeline_failed(pipeline_run_id, "match", match_result.get("error", ""))
    if await _is_cancelled(pipeline_run_id):
        return {"status": "cancelled"}

    apps_created = match_result.get("applications_created", 0)
    if apps_created == 0:
        logger.info("Pipeline %s — no matching applications, marking completed", pipeline_run_id)
        return await _set_pipeline_completed(pipeline_run_id)

    # --- Step 3: Apply for each pending application ---
    logger.info("Pipeline %s — applying for %d jobs", pipeline_run_id, apps_created)
    async with async_session_factory() as session:
        result = await session.execute(
            select(Application).where(
                Application.pipeline_run_id == pipeline_run_id,
                Application.status == "pending",
            ),
        )
        applications = list(result.scalars().all())

    from app.tasks.apply import _apply_to_job

    apply_results = []
    for app_row in applications:
        if await _is_cancelled(pipeline_run_id):
            logger.info("Pipeline %s cancelled during apply step", pipeline_run_id)
            return {"status": "cancelled"}
        logger.info("Pipeline %s — applying to application %s", pipeline_run_id, app_row.id)
        result = await _apply_to_job(app_row.id, user_id, pipeline_run_id)
        apply_results.append(result)

    # --- Step 4: Notify for each result ---
    from app.tasks.notify import _notify_result

    for app_row in applications:
        if await _is_cancelled(pipeline_run_id):
            logger.info("Pipeline %s cancelled during notify step", pipeline_run_id)
            return {"status": "cancelled"}
        logger.info("Pipeline %s — notifying for application %s", pipeline_run_id, app_row.id)
        try:
            await _notify_result(app_row.id, pipeline_run_id)
        except Exception as exc:
            logger.error("Notify failed for app %s: %s", app_row.id, exc)

    # --- Step 5: Mark completed ---
    return await _set_pipeline_completed(pipeline_run_id)


async def _set_pipeline_failed(pipeline_run_id: str, step: str, error: str) -> dict:
    """Update PipelineRun status to failed."""
    async with async_session_factory() as session:
        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline:
            pipeline.status = "failed"
            pipeline.error_step = step
            pipeline.error_msg = error
            pipeline.completed_at = datetime.now(timezone.utc)
            await session.commit()
    logger.error("Pipeline %s failed at step '%s': %s", pipeline_run_id, step, error)
    return {"status": "failed", "error_step": step, "error": error}


async def _set_pipeline_completed(pipeline_run_id: str) -> dict:
    """Update PipelineRun status to completed."""
    async with async_session_factory() as session:
        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline:
            pipeline.status = "completed"
            pipeline.completed_at = datetime.now(timezone.utc)
            await session.commit()
    logger.info("Pipeline %s completed", pipeline_run_id)
    return {"status": "completed"}
