import asyncio
import logging
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    WORKOUT_LOGGED = "workout_logged"
    PERSONAL_RECORD = "personal_record"


def emit(event_type: EventType, payload: dict[str, Any]) -> None:
    """Fire-and-forget: schedule an event handler as a background asyncio task."""
    asyncio.create_task(_safe_dispatch(event_type, payload))


async def _safe_dispatch(event_type: EventType, payload: dict[str, Any]) -> None:
    from app.events.handlers import handle
    try:
        await handle(event_type, payload)
    except Exception:
        logger.exception("Event handler failed for %s: %s", event_type, payload)
