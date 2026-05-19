import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.tasks.proactive_check import run_proactive_checks
from app.tasks.weekly_adaptation import run_weekly_adaptations
from app.tasks.weekly_recap import run_weekly_recaps

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
    _scheduler.add_job(
        run_weekly_recaps,
        trigger="cron",
        day_of_week="sun",
        hour=18,
        minute=0,
        id="weekly_recaps",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")


# ── Reminder scheduling ───────────────────────────────────────────────────────

async def _fire_reminder(reminder_id: str) -> None:
    from sqlalchemy import select
    from app.db.models import Reminder, User
    from app.db.session import AsyncSessionLocal
    from app.services.twilio_service import send_whatsapp_message

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
        reminder = result.scalar_one_or_none()
        if not reminder or not reminder.is_active:
            return
        user_result = await db.execute(select(User).where(User.id == reminder.user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.phone_number:
            return
        await send_whatsapp_message(user.phone_number, reminder.message)
        logger.info("Reminder fired: %s → %s", reminder.label, user.phone_number)


def _add_reminder_job(reminder) -> None:
    days = reminder.days
    day_of_week = "mon-sun" if "daily" in days else ",".join(d[:3] for d in days)
    _scheduler.add_job(
        _fire_reminder,
        trigger=CronTrigger(
            day_of_week=day_of_week,
            hour=reminder.hour,
            minute=reminder.minute,
            timezone=reminder.timezone,
        ),
        args=[reminder.id],
        id=f"reminder_{reminder.id}",
        replace_existing=True,
    )


def add_reminder(reminder) -> None:
    _add_reminder_job(reminder)


def remove_reminder(reminder_id: str) -> None:
    job_id = f"reminder_{reminder_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)


async def load_reminders() -> None:
    from sqlalchemy import select
    from app.db.models import Reminder
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Reminder).where(Reminder.is_active == True))
        reminders = result.scalars().all()

    for reminder in reminders:
        _add_reminder_job(reminder)
    logger.info("Loaded %d reminder(s) from DB", len(reminders))
