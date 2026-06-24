import asyncio
from app.database import async_session_factory
from app.models import PipelineRun, Portal
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(
            select(PipelineRun).order_by(PipelineRun.created_at.desc()).limit(4)
        )
        for r in result.scalars().all():
            p = await session.get(Portal, r.portal_id)
            pname = p.name if p else "?"
            if pname in ("LinkedIn", "Infojobs"):
                print(f"=== {pname} ({r.status}) ===")
                print(f"  Error: {r.error_msg}")
                if r.steps:
                    print(f"  Steps keys: {list(r.steps.keys())}")
                    for k, v in r.steps.items():
                        sv = str(v)
                        print(f"  {k}: {sv[:300]}")
                print()

asyncio.run(main())
