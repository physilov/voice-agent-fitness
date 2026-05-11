import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.tasks.proactive_check import run_proactive_checks
from app.tasks.weekly_adaptation import run_weekly_adaptations

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    _scheduler.add_job(
        run_proactive_checks,
        trigger="interval",
        hours=1,
        id="proactive_checks",
        replace_existing=True,
    )
    _scheduler.add_job(
        run_weekly_adaptations,
        trigger="cron",
        day_of_week="sun",
        hour=20,
        id="weekly_adaptations",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
