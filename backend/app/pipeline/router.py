"""Pipeline run endpoints."""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user_id
from app.database import get_session
from app.models import PipelineRun, Portal
from app.tasks.orchestrator import run_pipeline as run_pipeline_task

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"pending", "scraping", "matching", "applying", "notifying"}
CANCELLABLE_STATUSES = {"pending", "scraping", "matching", "applying", "notifying"}

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/latest")
async def latest_pipeline_runs(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Return the user's 10 most recent pipeline runs with portal name and status."""
    result = await session.execute(
        select(PipelineRun, Portal.name)
        .join(Portal, PipelineRun.portal_id == Portal.id, isouter=True)
        .where(PipelineRun.user_id == user_id)
        .order_by(PipelineRun.created_at.desc())
        .limit(10)
    )
    rows = result.all()

    runs_list = []
    for run, portal_name in rows:
        runs_list.append({
            "pipeline_run_id": run.id,
            "portal_name": portal_name or "Unknown",
            "status": run.status,
            "trigger": run.trigger,
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_step": run.error_step,
            "error_msg": run.error_msg,
        })

    return {
        "runs": runs_list,
        "has_active_runs": any(r.status in ACTIVE_STATUSES for r, _ in rows),
    }


@router.post("/run")
async def trigger_pipeline(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Trigger a pipeline run for all enabled portals of the current user."""
    # Get all enabled portals for this user (including built-in), deduplicated by name.
    # User-owned portals override built-in ones to prevent duplicate runs.
    result = await session.execute(
        select(Portal).where(
            Portal.is_enabled,
            (Portal.user_id == user_id) | (Portal.user_id.is_(None)),
        )
    )
    portals_raw = result.scalars().all()
    seen: dict[str, Portal] = {}
    for p in portals_raw:
        if p.name in seen:
            existing = seen[p.name]
            if existing.is_builtin and not p.is_builtin:
                seen[p.name] = p
        else:
            seen[p.name] = p
    portals = list(seen.values())

    if not portals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay portales habilitados. Activá al menos uno primero.",
        )

    runs = []
    for portal in portals:
        pipeline_run = PipelineRun(
            id=str(uuid4()),
            user_id=user_id,
            portal_id=portal.id,
            status="pending",
            trigger="manual",
        )
        session.add(pipeline_run)
        runs.append({
            "pipeline_run_id": pipeline_run.id,
            "portal_id": portal.id,
            "portal_name": portal.name,
            "status": "pending",
        })

    await session.commit()

    # Dispatch Celery tasks
    queued = 0
    failed = 0
    for run in runs:
        try:
            run_pipeline_task.delay(run["pipeline_run_id"])
            run["status"] = "queued"
            queued += 1
        except Exception as exc:
            logger.warning("Failed to dispatch Celery task for %s: %s", run["pipeline_run_id"], exc)
            run["status"] = "dispatch_failed"
            run["error"] = str(exc)
            failed += 1

    if queued == 0 and failed > 0:
        # All dispatches failed — Redis/Celery issue
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "No se pudieron encolar las tareas. "
                "Asegurate de que Redis esté corriendo y los workers de Celery estén activos."
            ),
        )

    message = f"Búsqueda iniciada para {queued} portal(es)"
    if failed:
        message += f" ({failed} fallaron)"

    return {
        "message": message,
        "runs": runs,
    }


@router.post("/{run_id}/cancel")
async def cancel_pipeline_run(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Cancel a pipeline run that hasn't completed yet."""
    try:
        result = await session.execute(
            select(PipelineRun).where(
                PipelineRun.id == run_id,
                PipelineRun.user_id == user_id,
            )
        )
        pipeline = result.scalar_one_or_none()
        if pipeline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pipeline run not found",
            )

        if pipeline.status not in CANCELLABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No se puede cancelar un pipeline con estado '{pipeline.status}'",
            )

        pipeline.status = "cancelled"
        pipeline.completed_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info("Pipeline %s cancelled by user", run_id)
        return {"status": "cancelled", "pipeline_run_id": run_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to cancel pipeline %s: %s", run_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cancelar el pipeline",
        )
