import logging
from typing import Any

from app.events import EventType

logger = logging.getLogger(__name__)


async def handle(event_type: EventType, payload: dict[str, Any]) -> None:
    if event_type == EventType.WORKOUT_LOGGED:
        await _on_workout_logged(payload)
    elif event_type == EventType.PERSONAL_RECORD:
        await _on_personal_record(payload)


async def _on_workout_logged(payload: dict[str, Any]) -> None:
    """Trigger plan adaptation if all of this week's sessions are now complete."""
    from app.agent.adaptation_agent import maybe_adapt_plan
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await maybe_adapt_plan(payload["user_id"], db)


async def _on_personal_record(payload: dict[str, Any]) -> None:
    logger.info(
        "PR: user=%s exercise=%s weight=%.1fkg",
        payload.get("user_id"),
        payload.get("exercise"),
        payload.get("weight_kg", 0),
    )
