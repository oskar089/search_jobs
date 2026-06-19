"""Celery task: send notifications for an application result."""

import asyncio
import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import async_session_factory
from app.models import Application, StoredJob, User

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def notify_result(
    self,  # noqa: ARG001
    application_id: str,
    pipeline_run_id: str,
) -> dict:
    """Send in-app and email notifications for a completed application."""
    return asyncio.run(_notify_result(application_id, pipeline_run_id))


async def _notify_result(
    application_id: str,
    pipeline_run_id: str,
) -> dict:
    from app.notifications.service import NotificationService

    # Load application + related data
    async with async_session_factory() as session:
        app_row = await session.get(Application, application_id)
        if app_row is None:
            raise ValueError(f"Application {application_id} not found")

        job = await session.get(StoredJob, app_row.stored_job_id)
        user = await session.get(User, app_row.user_id)

    if job is None or user is None:
        logger.warning("Skipping notify for %s — missing job or user", application_id)
        return {"status": "failed", "error": "Missing job or user"}

    # Dispatch notification
    service = NotificationService(async_session_factory)
    try:
        if app_row.status == "submitted":
            await service.notify_application_submitted(
                application_id=application_id,
                user_id=app_row.user_id,
                user_email=user.email,
                job_title=job.title,
                company=job.company,
            )
        elif app_row.status == "failed":
            await service.notify_application_failed(
                application_id=application_id,
                user_id=app_row.user_id,
                user_email=user.email,
                job_title=job.title,
                company=job.company,
                error=app_row.error_message or "Unknown error",
            )
        else:
            logger.info("Skipping notification for app %s — status=%s", application_id, app_row.status)
            return {"status": "skipped", "reason": f"Unhandled status: {app_row.status}"}
    except Exception as exc:
        logger.error("Notification failed for app %s: %s", application_id, exc)
        return {"status": "failed", "error": str(exc)}

    # Update pipeline steps
    async with async_session_factory() as session:
        from app.models import PipelineRun

        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline:
            step_key = f"notify:{application_id}"
            pipeline.steps = {
                **(pipeline.steps or {}),
                step_key: {"status": "completed"},
            }
            await session.commit()

    return {"status": "completed", "application_id": application_id}
