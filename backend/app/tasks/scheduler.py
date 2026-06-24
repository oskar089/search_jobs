"""Celery Beat task: periodic pipeline check for all enabled portals.

Scans all users who own at least one enabled portal, merges their portals
with built-in portals (deduplicating by name, user-owned overrides built-in),
creates a PipelineRun record per portal, and dispatches the orchestrator.
"""

import logging
from uuid import uuid4

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import async_session_factory
from app.models import PipelineRun, Portal
from app.tasks import run_async

logger = logging.getLogger(__name__)


@celery_app.task
def scheduled_pipeline_check() -> dict:
    """Entry point called by Celery Beat every 15 minutes."""
    return run_async(_scheduled_pipeline_check())


async def _scheduled_pipeline_check() -> dict:
    """Core logic: query enabled portals, group by user, create & dispatch runs."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Portal).where(Portal.is_enabled),
        )
        portals_raw = result.scalars().all()

    if not portals_raw:
        logger.info("No enabled portals found — skipping scheduled check")
        return {"status": "skipped", "reason": "no_enabled_portals"}

    # Separate built-in portals (user_id is None) from user-owned
    builtin_portals = [p for p in portals_raw if p.user_id is None]
    user_portals_map: dict[str, list[Portal]] = {}
    for p in portals_raw:
        if p.user_id is not None:
            user_portals_map.setdefault(p.user_id, []).append(p)

    if not user_portals_map:
        logger.info("No user-owned portals found — skipping scheduled check")
        return {"status": "skipped", "reason": "no_user_portals"}

    total_created = 0
    total_failed = 0

    for user_id, user_portals in user_portals_map.items():
        # Merge built-in portals with the user's own portals, deduplicating
        # by name.  User-owned portals override built-in ones (same logic as
        # app/pipeline/router.py trigger_pipeline).
        seen: dict[str, Portal] = {}
        for p in builtin_portals:
            seen[p.name] = p
        for p in user_portals:
            if p.name in seen:
                existing = seen[p.name]
                if existing.is_builtin and not p.is_builtin:
                    seen[p.name] = p
            else:
                seen[p.name] = p

        portals = list(seen.values())

        # --- Create PipelineRun records ---
        runs: list[dict[str, str]] = []
        async with async_session_factory() as session:
            for portal in portals:
                pipeline_run = PipelineRun(
                    id=str(uuid4()),
                    user_id=user_id,
                    portal_id=portal.id,
                    status="pending",
                    trigger="scheduled",
                )
                session.add(pipeline_run)
                runs.append({
                    "pipeline_run_id": pipeline_run.id,
                    "portal_id": portal.id,
                    "portal_name": portal.name,
                })
            await session.commit()

        # --- Dispatch Celery tasks (lazy import to avoid circular dependency) ---
        from app.tasks.orchestrator import run_pipeline as run_pipeline_task  # noqa: PLC0415
        for run in runs:
            try:
                run_pipeline_task.delay(run["pipeline_run_id"])
                total_created += 1
            except Exception as exc:
                logger.warning(
                    "Failed to dispatch pipeline %s: %s",
                    run["pipeline_run_id"], exc,
                )
                total_failed += 1

    logger.info(
        "Scheduled check complete — %d runs created, %d dispatch failures",
        total_created, total_failed,
    )

    return {
        "status": "completed",
        "runs_created": total_created,
        "dispatch_failures": total_failed,
    }
