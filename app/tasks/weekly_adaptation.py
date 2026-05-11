import logging

from sqlalchemy import select

from app.agent.adaptation_agent import run_adaptation_for_user
from app.db.models import User
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_weekly_adaptations() -> None:
    """Sunday 8pm UTC: review the completed week and write next week's plan for all users."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User.id))
        user_ids = result.scalars().all()

    logger.info("Weekly adaptation: evaluating %d users", len(user_ids))
    for user_id in user_ids:
        try:
            async with AsyncSessionLocal() as db:
                await run_adaptation_for_user(user_id, db)
        except Exception:
            logger.exception("Weekly adaptation failed for user %s", user_id)
