"""Celery task: scrape a portal and persist StoredJob rows."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import async_session_factory
from app.models import PipelineRun, Portal, StoredJob
from app.scrapers.engine import PortalSelectors, ScraperEngine

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_portal(
    self,  # noqa: ARG001 — Celery task instance (used by .retry())
    portal_id: str,
    user_id: str,
    pipeline_run_id: str,
) -> dict:
    """Scrape a portal and store job listings.

    Retries up to 3 times (60 s delay) on transient failures.
    """
    return asyncio.run(_scrape_portal(portal_id, user_id, pipeline_run_id))


async def _scrape_portal(
    portal_id: str,
    user_id: str,
    pipeline_run_id: str,
) -> dict:
    """Async implementation — called by the Celery task or the orchestrator."""

    # --- Load pipeline + portal ---
    async with async_session_factory() as session:
        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline is None:
            raise ValueError(f"PipelineRun {pipeline_run_id} not found")
        pipeline.status = "scraping"
        pipeline.error_step = None
        pipeline.error_msg = None
        await session.flush()

        portal = await session.get(Portal, portal_id)
        if portal is None:
            pipeline.status = "failed"
            pipeline.error_step = "scrape"
            pipeline.error_msg = f"Portal {portal_id} not found"
            await session.commit()
            return {"status": "failed", "error": f"Portal {portal_id} not found"}

        raw = portal.selectors
        selectors = PortalSelectors(
            job_card=raw.get("job_card", ""),
            title=raw.get("title", ""),
            company=raw.get("company", ""),
            location=raw.get("location"),
            description=raw.get("description", ""),
            url=raw.get("url", ""),
            salary=raw.get("salary"),
            posted_date=raw.get("posted_date"),
            apply_button=raw.get("apply_button"),
        )
        listing_url = portal.job_listing_url

    # --- Run the scraper (I/O-bound, no session held) ---
    try:
        async with ScraperEngine(headless=True, timeout=30000) as engine:
            scraped = await engine.scrape(listing_url, selectors, max_results=50)
    except Exception as exc:
        logger.error("Scrape failed for portal %s: %s", portal_id, exc)
        async with async_session_factory() as session:
            pipeline = await session.get(PipelineRun, pipeline_run_id)
            if pipeline:
                pipeline.status = "failed"
                pipeline.error_step = "scrape"
                pipeline.error_msg = str(exc)
                await session.commit()
        return {"status": "failed", "error": str(exc), "jobs_found": 0}

    # --- Persist new StoredJobs ---
    stored = 0
    async with async_session_factory() as session:
        for sj in scraped:
            if sj.external_id:
                existing = await session.execute(
                    select(StoredJob).where(
                        StoredJob.portal_id == portal_id,
                        StoredJob.external_id == sj.external_id,
                    ),
                )
                if existing.scalar_one_or_none():
                    continue

            job = StoredJob(
                portal_id=portal_id,
                external_id=sj.external_id,
                title=sj.title,
                company=sj.company,
                location=sj.location,
                description=sj.description,
                url=sj.url,
                salary_range=sj.salary_range,
                language=sj.language,
            )
            session.add(job)
            stored += 1

        pipeline = await session.get(PipelineRun, pipeline_run_id)
        if pipeline:
            pipeline.steps = {
                **(pipeline.steps or {}),
                "scrape": {
                    "status": "completed",
                    "jobs_found": len(scraped),
                    "jobs_stored": stored,
                },
            }
            await session.commit()

    logger.info("Scraped %d jobs from portal %s (%d new)", len(scraped), portal_id, stored)
    return {"status": "completed", "jobs_found": len(scraped), "jobs_stored": stored}
