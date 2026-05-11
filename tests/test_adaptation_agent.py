from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.adaptation_agent import (
    _current_week_number,
    maybe_adapt_plan,
    run_adaptation_for_user,
)
from app.db.models import WorkoutLog, WorkoutPlan


def _plan(weeks_old: int = 5, duration_weeks: int = 8) -> WorkoutPlan:
    return WorkoutPlan(
        id="plan-1",
        user_id="user-1",
        name="Test Plan",
        duration_weeks=duration_weeks,
        days_per_week=3,
        plan_data={
            "week_1": {
                "monday": [{"exercise": "squat", "sets": 3, "reps": 5, "weight_kg": 100}],
                "wednesday": [{"exercise": "bench", "sets": 3, "reps": 5, "weight_kg": 80}],
                "friday": [{"exercise": "deadlift", "sets": 1, "reps": 5, "weight_kg": 140}],
            }
        },
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=weeks_old * 7),
    )


def _db_returning(value):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


# ── _current_week_number ──────────────────────────────────────────────────────

def test_current_week_number_week_one():
    plan = _plan(weeks_old=0)
    assert _current_week_number(plan) == 1


def test_current_week_number_mid_plan():
    plan = _plan(weeks_old=3)
    assert _current_week_number(plan) == 4


def test_current_week_number_caps_at_duration():
    plan = _plan(weeks_old=20, duration_weeks=4)
    assert _current_week_number(plan) == 4


# ── run_adaptation_for_user ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_skips_user_with_no_active_plan(mocker):
    db = _db_returning(None)
    mock_claude = mocker.patch("app.agent.adaptation_agent.anthropic.AsyncAnthropic")
    await run_adaptation_for_user("user-1", db)
    mock_claude.assert_not_called()


@pytest.mark.asyncio
async def test_skips_final_week_of_plan(mocker):
    plan = _plan(weeks_old=7, duration_weeks=8)  # on week 8 — last week
    db = _db_returning(plan)
    mock_claude = mocker.patch("app.agent.adaptation_agent.anthropic.AsyncAnthropic")
    await run_adaptation_for_user("user-1", db)
    mock_claude.assert_not_called()


@pytest.mark.asyncio
async def test_skips_when_no_workouts_logged(mocker):
    plan = _plan(weeks_old=0)

    mock_workouts_result = MagicMock()
    mock_workouts_result.scalars.return_value.all.return_value = []

    mock_plan_result = MagicMock()
    mock_plan_result.scalar_one_or_none.return_value = plan

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[mock_plan_result, mock_workouts_result])

    mock_claude = mocker.patch("app.agent.adaptation_agent.anthropic.AsyncAnthropic")
    await run_adaptation_for_user("user-1", db)
    mock_claude.assert_not_called()


@pytest.mark.asyncio
async def test_updates_plan_on_tool_call(mocker):
    plan = _plan(weeks_old=0)
    workout = WorkoutLog(
        user_id="user-1",
        exercises=[{"name": "squat", "sets": [{"reps": 5, "weight_kg": 100}]}],
        logged_at=datetime.utcnow(),
    )

    mock_workouts_result = MagicMock()
    mock_workouts_result.scalars.return_value.all.return_value = [workout]
    mock_plan_result = MagicMock()
    mock_plan_result.scalar_one_or_none.return_value = plan

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[mock_plan_result, mock_workouts_result])
    db.commit = AsyncMock()

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "update_next_week_plan"
    tool_block.input = {
        "week_number": 2,
        "days": {"monday": [{"exercise": "squat", "sets": 3, "reps": 5, "weight_kg": 102.5}]},
        "adaptation_notes": "Increased squat weight 2.5%",
    }
    mock_response = MagicMock(content=[tool_block])

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    mocker.patch("app.agent.adaptation_agent.anthropic.AsyncAnthropic", return_value=mock_client)

    await run_adaptation_for_user("user-1", db)

    assert "week_2" in plan.plan_data
    assert plan.plan_data["week_2"]["monday"][0]["weight_kg"] == 102.5
    db.commit.assert_called_once()


# ── maybe_adapt_plan ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_maybe_adapt_triggers_when_week_complete(mocker):
    plan = _plan(weeks_old=0)  # week 1, has 3 prescribed days

    mock_plan_result = MagicMock()
    mock_plan_result.scalar_one_or_none.return_value = plan

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 3  # all 3 sessions logged

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[mock_plan_result, mock_count_result])

    mock_adapt = mocker.patch(
        "app.agent.adaptation_agent.run_adaptation_for_user", new=AsyncMock()
    )
    await maybe_adapt_plan("user-1", db)
    mock_adapt.assert_called_once_with("user-1", db)


@pytest.mark.asyncio
async def test_maybe_adapt_skips_when_week_incomplete(mocker):
    plan = _plan(weeks_old=0)  # 3 prescribed sessions

    mock_plan_result = MagicMock()
    mock_plan_result.scalar_one_or_none.return_value = plan

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 2  # only 2 of 3 done

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[mock_plan_result, mock_count_result])

    mock_adapt = mocker.patch(
        "app.agent.adaptation_agent.run_adaptation_for_user", new=AsyncMock()
    )
    await maybe_adapt_plan("user-1", db)
    mock_adapt.assert_not_called()
