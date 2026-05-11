import logging

from sqlalchemy import select

from app.agent.proactive_agent import run_proactive_check
from app.db.models import User
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_proactive_checks() -> None:
    """Hourly task: check every user and reach out if warranted.

    Each user gets its own DB session so a failure on one user doesn't
    affect the others.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User.id).where(User.phone_number.isnot(None)))
        user_ids = result.scalars().all()

    logger.info("Proactive check: evaluating %d users", len(user_ids))
    for user_id in user_ids:
        try:
            async with AsyncSessionLocal() as db:
                await run_proactive_check(user_id, db)
        except Exception:
            logger.exception("Proactive check failed for user %s", user_id)
