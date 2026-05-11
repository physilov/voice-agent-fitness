"""
Weekly plan adaptation agent.

After each week's sessions are logged, Claude reviews prescribed vs. actual
performance and writes the next week's plan with specific progressive overload
adjustments (weights, reps, exercise swaps).
"""
import json
import logging
from datetime import datetime, timedelta

import anthropic
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import WorkoutLog, WorkoutPlan

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert strength and conditioning coach reviewing an athlete's training week.

Compare what was prescribed against what was actually logged, then write the adapted
plan for next week using the update_next_week_plan tool.

Progressive overload rules:
- All prescribed reps completed at target weight → increase weight 2.5–5%
- Any sets missed or reps short → keep the same weight
- Workout note mentions form breakdown or pain → reduce weight 5–10%
- User skipped a session entirely → keep that session identical next week

Always use update_next_week_plan or no_changes_needed — never respond with plain text.
"""

_ADAPTATION_TOOLS = [
    {
        "name": "update_next_week_plan",
        "description": "Write the adapted workout plan for the upcoming week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "week_number": {
                    "type": "integer",
                    "description": "The week being written (e.g. 2 writes week_2 into the plan)",
                },
                "days": {
                    "type": "object",
                    "description": "Keys = day names (monday…sunday), values = exercise lists",
                    "additionalProperties": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "exercise": {"type": "string"},
                                "sets": {"type": "integer"},
                                "reps": {"type": "integer"},
                                "weight_kg": {"type": "number"},
                                "notes": {"type": "string"},
                            },
                            "required": ["exercise", "sets", "reps"],
                        },
                    },
                },
                "adaptation_notes": {
                    "type": "string",
                    "description": "One-line summary of the key changes made",
                },
            },
            "required": ["week_number", "days"],
        },
    },
    {
        "name": "no_changes_needed",
        "description": "Decide the plan does not need adaptation this week.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
]


def _current_week_number(plan: WorkoutPlan) -> int:
    days_elapsed = (datetime.utcnow() - plan.created_at).days
    return min(days_elapsed // 7 + 1, plan.duration_weeks)


def _week_bounds(plan: WorkoutPlan, week_number: int) -> tuple[datetime, datetime]:
    start = plan.created_at + timedelta(weeks=week_number - 1)
    return start, start + timedelta(weeks=1)


def _summarise_exercise(ex: dict) -> str:
    sets = ex.get("sets", [])
    set_str = " | ".join(
        f"{s.get('reps', '?')}r @ {s.get('weight_kg', 'bw')}kg" for s in sets
    )
    return f"{ex.get('name', '?')}: {set_str}"


def _build_context(plan: WorkoutPlan, week_num: int, workouts: list[WorkoutLog]) -> str:
    prescribed = plan.plan_data.get(f"week_{week_num}", {})
    actual_lines = []
    for log in workouts:
        day = log.logged_at.strftime("%A").lower()
        exercises = " / ".join(_summarise_exercise(e) for e in (log.exercises or []))
        note = f"  ← {log.notes}" if log.notes else ""
        actual_lines.append(f"  {day}: {exercises}{note}")

    return (
        f"Week {week_num} of {plan.duration_weeks} — '{plan.name}'\n\n"
        f"PRESCRIBED:\n{json.dumps(prescribed, indent=2)}\n\n"
        f"ACTUAL:\n" + ("\n".join(actual_lines) or "  (no sessions logged)") + "\n\n"
        f"Write the adapted plan for week {week_num + 1}."
    )


async def run_adaptation_for_user(user_id: str, db: AsyncSession) -> None:
    plan_result = await db.execute(
        select(WorkoutPlan)
        .where(WorkoutPlan.user_id == user_id, WorkoutPlan.is_active == True)
        .order_by(desc(WorkoutPlan.created_at))
        .limit(1)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        return

    week_num = _current_week_number(plan)
    if week_num >= plan.duration_weeks:
        return  # on the last week — nothing to write ahead

    week_start, week_end = _week_bounds(plan, week_num)
    workouts_result = await db.execute(
        select(WorkoutLog)
        .where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.logged_at >= week_start,
            WorkoutLog.logged_at < week_end,
        )
        .order_by(WorkoutLog.logged_at)
    )
    week_workouts = workouts_result.scalars().all()

    if not week_workouts:
        return  # nothing to adapt from

    context = _build_context(plan, week_num, week_workouts)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        tools=_ADAPTATION_TOOLS,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": context}],
    )

    for block in response.content:
        if block.type != "tool_use":
            continue
        if block.name == "update_next_week_plan":
            week_key = f"week_{block.input['week_number']}"
            plan.plan_data = {**plan.plan_data, week_key: block.input["days"]}
            await db.commit()
            logger.info(
                "Plan adapted — user=%s week=%d: %s",
                user_id,
                block.input["week_number"],
                block.input.get("adaptation_notes", ""),
            )
        elif block.name == "no_changes_needed":
            logger.debug("No adaptation for user %s: %s", user_id, block.input.get("reason"))
        break


async def maybe_adapt_plan(user_id: str, db: AsyncSession) -> None:
    """Called after a workout is logged. Only adapts when the week's sessions are complete."""
    plan_result = await db.execute(
        select(WorkoutPlan)
        .where(WorkoutPlan.user_id == user_id, WorkoutPlan.is_active == True)
        .order_by(desc(WorkoutPlan.created_at))
        .limit(1)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        return

    week_num = _current_week_number(plan)
    prescribed_count = len(plan.plan_data.get(f"week_{week_num}", {}))
    if prescribed_count == 0:
        return

    week_start, _ = _week_bounds(plan, week_num)
    count_result = await db.execute(
        select(func.count())
        .select_from(WorkoutLog)
        .where(WorkoutLog.user_id == user_id, WorkoutLog.logged_at >= week_start)
    )
    logged_count = count_result.scalar()

    if logged_count >= prescribed_count:
        await run_adaptation_for_user(user_id, db)
