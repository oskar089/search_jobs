"""Seed the database with built-in job portals for Argentina."""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Same DB URL as the app config
DATABASE_URL = (
    "postgresql+asyncpg://neondb_owner:npg_jM9hvZynakK0@"
    "ep-odd-block-ad1a5lon.c-2.us-east-1.aws.neon.tech/neondb?ssl=require"
)

from app.models.portal import Portal

BUILTIN_PORTALS = [
    {
        "name": "Bumeran",
        "base_url": "https://www.bumeran.com.ar",
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
    {
        "name": "Computrabajo",
        "base_url": "https://www.computrabajo.com.ar",
        "job_listing_url": "https://www.computrabajo.com.ar/empleos",
        "selectors": {
            "job_card": "article[data-id-oferta]",
            "title": "h2 a",
            "company": "p[class*='empr']",
            "location": "p[class*='loc']",
            "description": "div[class*='descripcion']",
            "url": "h2 a",
            "salary": "p[class*='sal']",
            "posted_date": "span[class*='fecha']",
            "apply_button": None,
        },
        "is_enabled": False,
    },
    {
        "name": "Infojobs",
        "base_url": "https://www.infojobs.net",
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
    {
        "name": "LinkedIn",
        "base_url": "https://www.linkedin.com",
        "job_listing_url": "https://www.linkedin.com/jobs/",
        "selectors": {
            "job_card": "li[data-occludable-job-id]",
            "title": "a.job-card-list__title",
            "company": "a.job-card-container__company-name",
            "location": "li.job-card-container__metadata-item",
            "description": None,
            "url": "a.job-card-list__title",
            "salary": None,
            "posted_date": "time",
            "apply_button": None,
        },
    },
]


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL, echo=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # Check if any builtin portals already exist
        result = await session.execute(
            select(Portal.id).where(Portal.is_builtin == True).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("✅ Built-in portals already exist, skipping seed.")
            await engine.dispose()
            return

        for p in BUILTIN_PORTALS:
            portal = Portal(
                name=p["name"],
                base_url=p["base_url"],
                job_listing_url=p["job_listing_url"],
                selectors=p["selectors"],
                is_builtin=True,
                is_enabled=p.get("is_enabled", True),
                scrape_interval_min=60,
            )
            session.add(portal)
            print(f"  + {p['name']} ({'enabled' if portal.is_enabled else 'disabled'})")

        await session.commit()
        print(f"\n✅ Seeded {len(BUILTIN_PORTALS)} built-in portals.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
