import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import NutritionLog, PersonalRecord, User, WeightLog, WorkoutLog
from app.db.session import AsyncSessionLocal
from app.services.card_generator import generate_weekly_recap_card
from app.services.media_store import save as save_media
from app.services.twilio_service import send_whatsapp_image

logger = logging.getLogger(__name__)


async def _recap_for_user(user: User, db: AsyncSession) -> None:
    if not user.phone_number:
        return

    now = datetime.utcnow()
    week_start = now - timedelta(days=7)

    # workouts this week
    result = await db.execute(
        select(WorkoutLog).where(
            WorkoutLog.user_id == user.id,
            WorkoutLog.logged_at >= week_start,
        )
    )
    workouts = result.scalars().all()

    # avg calories
    nut_result = await db.execute(
        select(NutritionLog).where(
            NutritionLog.user_id == user.id,
            NutritionLog.logged_at >= week_start,
        )
    )
    nutrition = nut_result.scalars().all()
    avg_calories = (
        sum(n.calories or 0 for n in nutrition) / len(nutrition) if nutrition else 0
    )

    # PRs this week
    pr_result = await db.execute(
        select(PersonalRecord).where(
            PersonalRecord.user_id == user.id,
            PersonalRecord.achieved_at >= week_start,
        )
    )
    prs = pr_result.scalars().all()

    # weight change
    wt_result = await db.execute(
        select(WeightLog)
        .where(WeightLog.user_id == user.id, WeightLog.logged_at >= week_start)
        .order_by(WeightLog.logged_at)
    )
    weight_logs = wt_result.scalars().all()
    weight_change = (
        round(weight_logs[-1].weight_kg - weight_logs[0].weight_kg, 1)
        if len(weight_logs) >= 2
        else 0.0
    )

    # Skip users with nothing to report
    if not workouts and not nutrition and not prs:
        return

    week_label = f"{week_start.strftime('%b %-d')} – {now.strftime('%b %-d')}"
    card_bytes = generate_weekly_recap_card(
        user_name=user.name or "Athlete",
        week_label=week_label,
        workouts=len(workouts),
        avg_calories=avg_calories,
        prs_hit=len(prs),
        weight_change_kg=weight_change,
    )
    filename = save_media(card_bytes)
    media_url = f"{settings.base_url}/media/{filename}"
    caption = f"Your weekly recap is ready, {user.name or 'Athlete'}! Keep it up 💪"
    await send_whatsapp_image(user.phone_number, media_url, caption)
    logger.info("Weekly recap sent to user %s", user.id)


async def run_weekly_recaps() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.phone_number.isnot(None)))
        users = result.scalars().all()

    for user in users:
        try:
            async with AsyncSessionLocal() as db:
                # re-fetch user in new session
                result = await db.execute(select(User).where(User.id == user.id))
                u = result.scalar_one_or_none()
                if u:
                    await _recap_for_user(u, db)
        except Exception:
            logger.exception("Weekly recap failed for user %s", user.id)
