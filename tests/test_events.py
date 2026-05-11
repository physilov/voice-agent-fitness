import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.events import EventType, emit


def test_emit_schedules_background_task(mocker):
    mock_create_task = mocker.patch("app.events.asyncio.create_task")
    emit(EventType.WORKOUT_LOGGED, {"user_id": "user-1"})
    mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_workout_logged_event_calls_maybe_adapt(mocker):
    mock_adapt = mocker.patch(
        "app.events.handlers._on_workout_logged", new=AsyncMock()
    )
    from app.events.handlers import handle
    await handle(EventType.WORKOUT_LOGGED, {"user_id": "user-1"})
    mock_adapt.assert_called_once_with({"user_id": "user-1"})


@pytest.mark.asyncio
async def test_safe_dispatch_swallows_exceptions(mocker):
    mocker.patch(
        "app.events.handlers.handle",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    )
    from app.events import _safe_dispatch
    # Should not raise
    await _safe_dispatch(EventType.WORKOUT_LOGGED, {"user_id": "user-1"})
