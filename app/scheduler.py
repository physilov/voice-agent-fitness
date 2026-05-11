import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.tasks.proactive_check import run_proactive_checks

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
    _scheduler.start()
    logger.info("Scheduler started — proactive checks every hour")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
