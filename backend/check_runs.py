"""Check recent pipeline runs."""
import asyncio
from datetime import datetime, timezone, timedelta

from app.database import async_session_factory
from app.models import PipelineRun, Portal
from sqlalchemy import select


async def main():
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with async_session_factory() as session:
        result = await session.execute(
            select(PipelineRun)
            .where(PipelineRun.created_at > cutoff)
            .order_by(PipelineRun.created_at.desc())
        )
        runs = result.scalars().all()
        if not runs:
            print("No recent pipeline runs found in the last 10 minutes.")
            return
        for r in runs:
            portal = await session.get(Portal, r.portal_id)
            pname = portal.name if portal else "Unknown"
            print(
                f"  {pname:15s} | status={r.status:12s} | "
                f"created={r.created_at.strftime('%H:%M:%S')} | "
                f"trigger={r.trigger}"
            )
        print(f"\nTotal: {len(runs)} runs")


asyncio.run(main())
