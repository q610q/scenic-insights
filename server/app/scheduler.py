"""APScheduler — refresh materialized views nightly."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from app.cache import cache_invalidate
from app.config import settings
from app.db import SessionLocal

log = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def refresh_materialized_views() -> None:
    """REFRESH MATERIALIZED VIEW CONCURRENTLY (mv_*)."""
    async with SessionLocal() as session:
        log.info("Refreshing materialized views...")
        for mv in ("mv_spot_metrics", "mv_comment_monthly", "mv_city_summary"):
            await session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}"))
        await session.execute(text("REFRESH MATERIALIZED VIEW mv_level_dist"))
        await session.commit()
        log.info("Materialized views refreshed.")

    # 清理大屏缓存
    n = await cache_invalidate("dashboard:")
    log.info("Invalidated %s dashboard cache entries.", n)


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(
        refresh_materialized_views,
        CronTrigger(hour=settings.MV_REFRESH_CRON_HOUR, minute=0),
        id="refresh_mvs",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    _scheduler.start()
    log.info(
        "Scheduler started, mv refresh at %02d:00 daily.",
        settings.MV_REFRESH_CRON_HOUR,
    )
    return _scheduler


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
