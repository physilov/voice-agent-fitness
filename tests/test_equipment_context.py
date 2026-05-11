from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.fitness_agent import _maybe_restore_equipment
from app.agent.prompts import _equipment_section, build_system_prompt
from app.agent.tools import handle_tool_call
from app.db.models import User


@pytest.fixture
def user():
    return User(
        id="user-1",
        phone_number="+15551234567",
        name="Alex",
        equipment=["barbell", "dumbbells", "pull-up bar"],
        default_equipment=None,
        equipment_context_note=None,
        equipment_context_expires_at=None,
    )


# ── Prompt rendering ──────────────────────────────────────────────────────────

def test_prompt_no_context(user):
    section = _equipment_section(user)
    assert section == "Equipment: barbell, dumbbells, pull-up bar"
    assert "Default" not in section


def test_prompt_shows_context_note(user):
    user.equipment = ["bodyweight"]
    user.default_equipment = ["barbell", "dumbbells", "pull-up bar"]
    user.equipment_context_note = "camping trip"
    section = _equipment_section(user)
    assert "camping trip" in section
    assert "bodyweight" in section
    assert "barbell" in section
    assert "Default" in section


def test_prompt_shows_expiry_date(user):
    user.equipment = ["dumbbells"]
    user.default_equipment = ["barbell"]
    user.equipment_context_note = "hotel gym"
    user.equipment_context_expires_at = datetime(2026, 6, 15)
    section = _equipment_section(user)
    assert "Jun 15" in section


# ── Tool handler: update_equipment_context ────────────────────────────────────

@pytest.mark.asyncio
async def test_saves_default_equipment_on_first_context(user):
    db = AsyncMock()
    db.commit = AsyncMock()

    result, ui = await handle_tool_call(
        "update_equipment_context",
        {"equipment": ["bodyweight"], "context_note": "camping"},
        user,
        db,
    )

    assert user.default_equipment == ["barbell", "dumbbells", "pull-up bar"]
    assert user.equipment == ["bodyweight"]
    assert user.equipment_context_note == "camping"
    assert "camping" in result
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sets_expiry_when_days_provided(user):
    db = AsyncMock()
    db.commit = AsyncMock()
    before = datetime.utcnow()

    await handle_tool_call(
        "update_equipment_context",
        {"equipment": ["dumbbells"], "context_note": "hotel", "expires_in_days": 5},
        user,
        db,
    )

    assert user.equipment_context_expires_at is not None
    delta = user.equipment_context_expires_at - before
    assert 4 <= delta.days <= 5


@pytest.mark.asyncio
async def test_restore_default_equipment_tool(user):
    user.equipment = ["bodyweight"]
    user.default_equipment = ["barbell", "dumbbells"]
    user.equipment_context_note = "camping"
    db = AsyncMock()
    db.commit = AsyncMock()

    result, _ = await handle_tool_call("restore_default_equipment", {}, user, db)

    assert user.equipment == ["barbell", "dumbbells"]
    assert user.equipment_context_note is None
    assert "barbell" in result


# ── Auto-restoration ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_maybe_restore_expired_context(user):
    user.equipment = ["bodyweight"]
    user.default_equipment = ["barbell", "dumbbells"]
    user.equipment_context_note = "camping trip"
    user.equipment_context_expires_at = datetime.utcnow() - timedelta(hours=1)
    db = AsyncMock()
    db.commit = AsyncMock()

    await _maybe_restore_equipment(user, db)

    assert user.equipment == ["barbell", "dumbbells"]
    assert user.equipment_context_note is None
    assert user.equipment_context_expires_at is None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_maybe_restore_skips_unexpired_context(user):
    user.equipment = ["bodyweight"]
    user.default_equipment = ["barbell"]
    user.equipment_context_note = "camping"
    user.equipment_context_expires_at = datetime.utcnow() + timedelta(days=2)
    db = AsyncMock()
    db.commit = AsyncMock()

    await _maybe_restore_equipment(user, db)

    assert user.equipment == ["bodyweight"]  # unchanged
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_maybe_restore_skips_when_no_expiry(user):
    user.equipment_context_expires_at = None
    db = AsyncMock()
    db.commit = AsyncMock()

    await _maybe_restore_equipment(user, db)

    db.commit.assert_not_called()
