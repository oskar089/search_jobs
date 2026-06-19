import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user_id
from app.database import get_session
from app.models import Portal
from app.portals.schemas import PortalCreate, PortalResponse, PortalUpdate
from app.scrapers.engine import PortalSelectors as EngineSelectors, ScraperEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portals", tags=["portals"])


async def _get_portal_or_404(
    portal_id: str,
    session: AsyncSession,
) -> Portal:
    """Fetch a portal by ID or raise 404."""
    result = await session.execute(select(Portal).where(Portal.id == portal_id))
    portal = result.scalar_one_or_none()
    if portal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal not found",
        )
    return portal


def _assert_owner(portal: Portal, user_id: str) -> None:
    """Raise 403 if the current user does not own the portal."""
    if portal.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in portals cannot be modified",
        )
    if portal.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this portal",
        )


@router.get("", response_model=list[PortalResponse])
async def list_portals(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """List the current user's portals and all built-in portals."""
    result = await session.execute(
        select(Portal).where(
            or_(
                Portal.user_id == user_id,
                Portal.user_id.is_(None),
            ),
        ).order_by(Portal.name),
    )
    return result.scalars().all()


@router.post("", response_model=PortalResponse, status_code=status.HTTP_201_CREATED)
async def create_portal(
    body: PortalCreate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new portal configuration for the current user."""
    portal = Portal(
        user_id=user_id,
        name=body.name,
        base_url=body.base_url,
        job_listing_url=body.job_listing_url,
        selectors=body.selectors.model_dump(),
        scrape_interval_min=body.scrape_interval_min,
    )
    session.add(portal)
    await session.flush()
    return portal


@router.get("/{portal_id}", response_model=PortalResponse)
async def get_portal(
    portal_id: str,
    session: AsyncSession = Depends(get_session),
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001 — ensures auth
):
    """Get a single portal configuration by ID."""
    return await _get_portal_or_404(portal_id, session)


@router.put("/{portal_id}", response_model=PortalResponse)
async def update_portal(
    portal_id: str,
    body: PortalUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Update a portal configuration (owner only)."""
    portal = await _get_portal_or_404(portal_id, session)
    _assert_owner(portal, user_id)

    update_data = body.model_dump(exclude_unset=True)
    if "selectors" in update_data and body.selectors is not None:
        update_data["selectors"] = body.selectors.model_dump()

    for field, value in update_data.items():
        setattr(portal, field, value)

    await session.flush()
    return portal


@router.delete("/{portal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portal(
    portal_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a portal configuration (owner only)."""
    portal = await _get_portal_or_404(portal_id, session)
    _assert_owner(portal, user_id)

    await session.delete(portal)
    await session.flush()


@router.patch("/{portal_id}/toggle", response_model=PortalResponse)
async def toggle_portal(
    portal_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Toggle the enabled/disabled state of a portal (owner only)."""
    portal = await _get_portal_or_404(portal_id, session)
    _assert_owner(portal, user_id)

    portal.is_enabled = not portal.is_enabled
    await session.flush()
    return portal


@router.post("/{portal_id}/dry-run")
async def dry_run_portal(
    portal_id: str,
    test_url: str | None = Query(
        default=None,
        description="Override the portal's job_listing_url for this test run",
    ),
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001 — ensures auth
    session: AsyncSession = Depends(get_session),
):
    """Run a dry‑run scrape against a portal and return parsed jobs without persisting.

    Accepts an optional `test_url` query parameter to override the portal's
    configured `job_listing_url` — useful for testing with a different search
    or a local HTML fixture.
    """
    portal = await _get_portal_or_404(portal_id, session)

    # Build engine‑compatible selectors from the stored JSON
    raw: dict[str, Any] = portal.selectors
    selectors = EngineSelectors(
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

    url = test_url or portal.job_listing_url

    try:
        async with ScraperEngine(headless=True, timeout=30000) as engine:
            jobs = await engine.dry_run(url, selectors)
    except Exception as exc:
        logger.error("Dry-run failed for portal %s: %s", portal_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Dry-run scrape failed: {exc}",
        ) from exc

    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dry-run returned zero results. Check your selectors or the portal URL.",
        )

    return {
        "portal_id": portal_id,
        "portal_name": portal.name,
        "url": url,
        "jobs": [
            {
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "description": j.description[:500] if j.description else "",
                "url": j.url,
                "salary_range": j.salary_range,
                "posted_at": j.posted_at,
            }
            for j in jobs
        ],
        "total": len(jobs),
    }
