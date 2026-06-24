"""Update portal selectors with real working selectors found via Playwright analysis."""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = (
    "postgresql+asyncpg://neondb_owner:npg_jM9hvZynakK0@"
    "ep-odd-block-ad1a5lon.c-2.us-east-1.aws.neon.tech/neondb?ssl=require"
)

from app.models.portal import Portal
from app.models.pipeline_run import PipelineRun


UPDATED_PORTALS = {
    "Bumeran": {
        "job_listing_url": "https://www.bumeran.com.ar/empleos/",
        "selectors": {
            "job_card": "a[href*='/empleos/'][href$='.html']",
            "title": "h2",
            "company": "h3",
            "location": None,
            "description": "p",
            "url": "a[href*='/empleos/']",
            "salary": None,
            "posted_date": None,
            "apply_button": None,
        },
    },
    "Infojobs": {
        "job_listing_url": "https://www.infojobs.net/ofertas-trabajo",
        "selectors": {
            "job_card": "div.ij-OfferCardContent",
            "title": "a.ij-OfferCardContent-description-link span.ij-OfferCardContent-description-title-link",
            "company": "a.ij-OfferCardContent-description-subtitle-link",
            "location": "ul.ij-OfferCardContent-description-list li",
            "description": "p.ij-OfferCardContent-description-description",
            "url": "a.ij-OfferCardContent-description-link",
            "salary": None,
            "posted_date": None,
            "apply_button": None,
        },
    },
}


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # 1. Update selectors for known portals
        result = await session.execute(
            select(Portal).where(Portal.is_builtin == True)
        )
        portals = result.scalars().all()

        for portal in portals:
            if portal.name in UPDATED_PORTALS:
                data = UPDATED_PORTALS[portal.name]
                portal.job_listing_url = data["job_listing_url"]
                portal.selectors = data["selectors"]
                portal.is_verified = True
                print(f"  [OK] {portal.name} — selectors updated")

        # 2. Disable Computrabajo (blocked by Cloudflare, un-scrapable)
        compu = await session.execute(
            select(Portal).where(Portal.name == "Computrabajo")
        )
        compu_portal = compu.scalar_one_or_none()
        if compu_portal:
            compu_portal.is_enabled = False
            compu_portal.is_verified = False
            print(f"  [DISABLED] Computrabajo — disabled (blocked by Cloudflare)")

        # 3. Mark all stuck "pending" PipelineRuns as "failed"
        result2 = await session.execute(
            select(PipelineRun).where(PipelineRun.status.in_(["pending", "scraping"]))
        )
        stuck = result2.scalars().all()
        now = datetime.now(timezone.utc)
        for run in stuck:
            run.status = "failed"
            run.error_step = "stale"
            run.error_msg = "Cancelado — selectores fueron actualizados"
            run.completed_at = now
        if stuck:
            print(f"  [CLEANUP] Marked {len(stuck)} stale pipeline runs as failed")

        await session.commit()
        print(f"\n[DONE] {len(UPDATED_PORTALS)} portals updated, {len(stuck)} stale runs cleaned.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
