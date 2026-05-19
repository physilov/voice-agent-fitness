import json
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

import anthropic
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.response_schema import UIComponent
from app.config import settings
from app.db.models import NutritionLog, PersonalRecord, Reminder, User, WeightLog, WorkoutLog, WorkoutPlan
from app.events import EventType, emit
from app.services.exercisedb import exercisedb_service
from app.services.usda_food import search_food as usda_search_food

# ── Tool definitions (passed directly to the Claude API) ─────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "update_user_profile",
        "description": (
            "Update the user's profile. Call as soon as the user shares any personal detail — "
            "name, age, weight, height, goal, fitness level, equipment, or preferred schedule. "
            "Don't wait to collect everything first; save each piece as it arrives."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "weight_kg": {"type": "number"},
                "height_cm": {"type": "number"},
                "fitness_level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                },
                "goals": {"type": "array", "items": {"type": "string"}},
                "equipment": {"type": "array", "items": {"type": "string"}},
                "preferred_days": {"type": "array", "items": {"type": "string"}},
                "timezone": {"type": "string"},
            },
        },
    },
    {
        "name": "generate_workout_plan",
        "description": (
            "Generate and save a personalized multi-week workout plan for the user. "
            "Omit plan_data to have the plan content reasoned out automatically based on the user's profile. "
            "Supply plan_data only when you already have a fully-specified structure to save."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "e.g. '12-Week Strength Builder'"},
                "duration_weeks": {"type": "integer"},
                "days_per_week": {"type": "integer"},
                "plan_data": {
                    "type": "object",
                    "description": (
                        "Optional. Structured plan: "
                        "{week_1: {monday: [{exercise, sets, reps, rest_seconds}]}}. "
                        "Omit to auto-generate from the user's profile."
                    ),
                },
            },
            "required": ["name", "duration_weeks", "days_per_week"],
        },
    },
    {
        "name": "get_current_plan",
        "description": "Retrieve the user's active workout plan.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "log_workout",
        "description": "Log a completed workout session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "exercises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "sets": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "reps": {"type": "integer"},
                                        "weight_kg": {"type": "number"},
                                    },
                                },
                            },
                            "notes": {"type": "string"},
                        },
                        "required": ["name", "sets"],
                    },
                },
                "duration_minutes": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": ["exercises"],
        },
    },
    {
        "name": "search_food",
        "description": (
            "Look up nutrition data for a food from the USDA database. "
            "Always call this before log_nutrition so macros are accurate. "
            "Returns up to 5 matches with calories, protein, carbs, fat per 100 g."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Food name to search, e.g. 'grilled chicken breast' or 'brown rice cooked'",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "log_nutrition",
        "description": "Log a meal or daily nutrition intake.",
        "input_schema": {
            "type": "object",
            "properties": {
                "meal_name": {"type": "string"},
                "calories": {"type": "number"},
                "protein_g": {"type": "number"},
                "carbs_g": {"type": "number"},
                "fat_g": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["meal_name", "calories"],
        },
    },
    {
        "name": "get_progress_summary",
        "description": "Get a summary of the user's workout and nutrition progress over a period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_days": {"type": "integer", "description": "Days to look back (e.g. 30, 90)"},
                "metric": {
                    "type": "string",
                    "enum": ["workouts", "nutrition", "all"],
                    "default": "all",
                },
            },
            "required": ["period_days"],
        },
    },
    {
        "name": "check_personal_record",
        "description": "Check if a lift is a personal record and update if so. Call after logging any weighted exercise.",
        "input_schema": {
            "type": "object",
            "properties": {
                "exercise_name": {"type": "string"},
                "weight_kg": {"type": "number"},
                "reps": {"type": "integer"},
            },
            "required": ["exercise_name", "weight_kg", "reps"],
        },
    },
    {
        "name": "get_personal_records",
        "description": "Retrieve personal records for one or all exercises.",
        "input_schema": {
            "type": "object",
            "properties": {
                "exercise_name": {
                    "type": "string",
                    "description": "Omit to retrieve all PRs",
                },
            },
        },
    },
    {
        "name": "show_exercise_animation",
        "description": (
            "Display an exercise animation with instructions. "
            "Call whenever explaining how to perform an exercise."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "exercise_name": {"type": "string"},
                "coaching_cues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "2-4 key coaching points displayed alongside the animation",
                },
            },
            "required": ["exercise_name", "coaching_cues"],
        },
    },
    {
        "name": "update_equipment_context",
        "description": (
            "Update available equipment for the user's current situation. "
            "Call whenever they mention traveling, camping, a hotel, visiting a gym, "
            "or any change in location or available equipment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "equipment": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Equipment currently available, e.g. ['bodyweight'] or ['dumbbells', 'cables']",
                },
                "context_note": {
                    "type": "string",
                    "description": "Brief label for the situation, e.g. 'camping trip', 'hotel gym', 'traveling'",
                },
                "expires_in_days": {
                    "type": "integer",
                    "description": "Days until default equipment is automatically restored. Omit if open-ended.",
                },
            },
            "required": ["equipment", "context_note"],
        },
    },
    {
        "name": "restore_default_equipment",
        "description": "Restore the user's default home equipment when they return from a trip or change of location.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "log_weight",
        "description": "Log the user's body weight. Call whenever the user mentions their current weight.",
        "input_schema": {
            "type": "object",
            "properties": {
                "weight_kg": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["weight_kg"],
        },
    },
    {
        "name": "get_weight_trend",
        "description": "Show the user's weight history as a chart. Call when they ask about weight progress or trends.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_days": {"type": "integer", "description": "Days to look back (e.g. 30, 90)"},
            },
            "required": ["period_days"],
        },
    },
    {
        "name": "schedule_reminder",
        "description": (
            "Schedule a recurring WhatsApp reminder for the user. "
            "Call when the user asks to be reminded about workouts, logging meals, or any habit."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Short name, e.g. 'Morning workout'"},
                "message": {"type": "string", "description": "The message to send, e.g. 'Time to hit the gym!'"},
                "days": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["daily", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                    },
                    "description": "Days to send the reminder. Use ['daily'] for every day.",
                },
                "hour": {"type": "integer", "description": "Hour in 24h format (0-23) in the user's timezone"},
                "minute": {"type": "integer", "description": "Minute (0-59), defaults to 0"},
            },
            "required": ["label", "message", "days", "hour"],
        },
    },
    {
        "name": "list_reminders",
        "description": "List all active reminders for the user.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "cancel_reminder",
        "description": "Cancel an active reminder by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reminder_id": {"type": "string"},
            },
            "required": ["reminder_id"],
        },
    },
]


# ── Plan generation with extended thinking ───────────────────────────────────

async def _generate_plan_with_thinking(
    user: User,
    name: str,
    duration_weeks: int,
    days_per_week: int,
) -> dict:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"Generate a detailed {duration_weeks}-week workout plan called \"{name}\" "
        f"for {days_per_week} training days per week.\n\n"
        f"User profile:\n"
        f"- Fitness level: {user.fitness_level or 'not specified'}\n"
        f"- Goals: {', '.join(user.goals or []) or 'not specified'}\n"
        f"- Equipment: {', '.join(user.equipment or []) or 'not specified'}\n"
        f"- Notes: {user.memory_summary or 'none'}\n\n"
        "Return ONLY a valid JSON object (no markdown fences) with this structure:\n"
        '{"week_1": {"monday": [{"exercise": "...", "sets": 3, "reps": 10, "rest_seconds": 60}], ...}, "week_2": {...}, ...}\n\n'
        "Use only the listed equipment. Make the plan progressive across weeks."
    )

    response = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": prompt}],
    )

    text = next((block.text for block in response.content if hasattr(block, "text")), "{}")
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        text = match.group(1)
    return json.loads(text)


# ── Tool handlers ─────────────────────────────────────────────────────────────

async def handle_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    user: User,
    db: AsyncSession,
) -> tuple[str, list[UIComponent]]:
    ui: list[UIComponent] = []

    if tool_name == "update_user_profile":
        for field, value in tool_input.items():
            if hasattr(user, field):
                setattr(user, field, value)
        await db.commit()
        return "Profile updated.", ui

    if tool_name == "generate_workout_plan":
        plan_data = tool_input.get("plan_data")
        if not plan_data:
            plan_data = await _generate_plan_with_thinking(
                user,
                tool_input["name"],
                tool_input["duration_weeks"],
                tool_input["days_per_week"],
            )
        existing = await db.execute(
            select(WorkoutPlan).where(
                WorkoutPlan.user_id == user.id, WorkoutPlan.is_active == True
            )
        )
        for plan in existing.scalars():
            plan.is_active = False
        plan = WorkoutPlan(
            user_id=user.id,
            name=tool_input["name"],
            duration_weeks=tool_input["duration_weeks"],
            days_per_week=tool_input["days_per_week"],
            plan_data=plan_data,
        )
        db.add(plan)
        await db.commit()
        return f"Workout plan '{tool_input['name']}' created and activated.", ui

    if tool_name == "get_current_plan":
        result = await db.execute(
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user.id, WorkoutPlan.is_active == True)
            .order_by(desc(WorkoutPlan.created_at))
            .limit(1)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            return "No active workout plan.", ui
        ui.append(UIComponent(
            type="workout_plan_card",
            data={"name": plan.name, "plan": plan.plan_data},
        ))
        return f"Active plan: {plan.name} ({plan.duration_weeks} weeks, {plan.days_per_week} days/week).", ui

    if tool_name == "log_workout":
        log = WorkoutLog(
            user_id=user.id,
            exercises=tool_input["exercises"],
            duration_minutes=tool_input.get("duration_minutes"),
            notes=tool_input.get("notes"),
        )
        db.add(log)
        await db.commit()
        emit(EventType.WORKOUT_LOGGED, {"user_id": user.id})
        names = [e["name"] for e in tool_input["exercises"]]
        return f"Workout logged: {', '.join(names)}.", ui

    if tool_name == "log_nutrition":
        log = NutritionLog(
            user_id=user.id,
            meal_name=tool_input["meal_name"],
            calories=tool_input["calories"],
            protein_g=tool_input.get("protein_g"),
            carbs_g=tool_input.get("carbs_g"),
            fat_g=tool_input.get("fat_g"),
            notes=tool_input.get("notes"),
        )
        db.add(log)
        await db.commit()
        ui.append(UIComponent(
            type="nutrition_breakdown",
            data={
                "meal": tool_input["meal_name"],
                "calories": tool_input["calories"],
                "protein_g": tool_input.get("protein_g"),
                "carbs_g": tool_input.get("carbs_g"),
                "fat_g": tool_input.get("fat_g"),
            },
        ))
        return f"Logged {tool_input['meal_name']}: {tool_input['calories']} kcal.", ui

    if tool_name == "get_progress_summary":
        since = datetime.utcnow() - timedelta(days=tool_input["period_days"])
        metric = tool_input.get("metric", "all")
        parts: list[str] = []

        if metric in ("workouts", "all"):
            result = await db.execute(
                select(WorkoutLog)
                .where(WorkoutLog.user_id == user.id, WorkoutLog.logged_at >= since)
                .order_by(WorkoutLog.logged_at)
            )
            logs = result.scalars().all()
            parts.append(f"Workouts: {len(logs)}")
            if logs:
                all_exercises = [e["name"] for log in logs for e in log.exercises]
                top = Counter(all_exercises).most_common(3)
                parts.append(f"Top: {', '.join(f'{n} ({c}x)' for n, c in top)}")
            ui.append(UIComponent(
                type="progress_chart",
                data={
                    "period_days": tool_input["period_days"],
                    "workout_count": len(logs),
                    "workout_dates": [log.logged_at.isoformat() for log in logs],
                },
            ))

        if metric in ("nutrition", "all"):
            result = await db.execute(
                select(NutritionLog).where(
                    NutritionLog.user_id == user.id, NutritionLog.logged_at >= since
                )
            )
            nutrition_logs = result.scalars().all()
            if nutrition_logs:
                avg_cals = sum(n.calories or 0 for n in nutrition_logs) / len(nutrition_logs)
                parts.append(f"Avg daily calories: {avg_cals:.0f} kcal")

        return " | ".join(parts) or "No data for this period.", ui

    if tool_name == "check_personal_record":
        exercise = tool_input["exercise_name"]
        weight = tool_input["weight_kg"]
        reps = tool_input["reps"]
        result = await db.execute(
            select(PersonalRecord)
            .where(PersonalRecord.user_id == user.id, PersonalRecord.exercise_name == exercise)
            .order_by(desc(PersonalRecord.weight_kg))
            .limit(1)
        )
        existing_pr = result.scalar_one_or_none()
        if not existing_pr or weight > existing_pr.weight_kg:
            db.add(PersonalRecord(user_id=user.id, exercise_name=exercise, weight_kg=weight, reps=reps))
            await db.commit()
            ui.append(UIComponent(
                type="pr_celebration",
                data={
                    "exercise": exercise,
                    "weight_kg": weight,
                    "reps": reps,
                    "previous_kg": existing_pr.weight_kg if existing_pr else None,
                },
            ))
            emit(EventType.PERSONAL_RECORD, {"user_id": user.id, "exercise": exercise, "weight_kg": weight})
            # Send PR card via WhatsApp (non-blocking — don't fail if it errors)
            try:
                from app.services.card_generator import generate_pr_card
                from app.services.media_store import save as save_media
                from app.services.twilio_service import send_whatsapp_image
                card_bytes = generate_pr_card(
                    user_name=user.name or "Athlete",
                    exercise=exercise,
                    weight_kg=weight,
                    reps=reps,
                    previous_kg=existing_pr.weight_kg if existing_pr else None,
                )
                filename = save_media(card_bytes)
                from app.config import settings as _settings
                media_url = f"{_settings.base_url}/media/{filename}"
                if user.phone_number:
                    await send_whatsapp_image(
                        user.phone_number,
                        media_url,
                        f"🏆 New PR on {exercise}: {weight}kg × {reps} reps!",
                    )
            except Exception:
                pass  # card send failure must never break the tool response
            return f"NEW PERSONAL RECORD on {exercise}: {weight}kg x {reps} reps!", ui
        return f"Not a PR. Current best: {existing_pr.weight_kg}kg.", ui

    if tool_name == "get_personal_records":
        exercise = tool_input.get("exercise_name")
        query = select(PersonalRecord).where(PersonalRecord.user_id == user.id)
        if exercise:
            query = query.where(PersonalRecord.exercise_name == exercise)
        result = await db.execute(query.order_by(desc(PersonalRecord.achieved_at)))
        prs = result.scalars().all()
        if not prs:
            return "No personal records yet.", ui
        lines = [f"{pr.exercise_name}: {pr.weight_kg}kg x {pr.reps} reps" for pr in prs]
        return "Personal records:\n" + "\n".join(lines), ui

    if tool_name == "update_equipment_context":
        if user.default_equipment is None:
            user.default_equipment = user.equipment or []
        user.equipment = tool_input["equipment"]
        user.equipment_context_note = tool_input["context_note"]
        if tool_input.get("expires_in_days"):
            user.equipment_context_expires_at = datetime.utcnow() + timedelta(
                days=tool_input["expires_in_days"]
            )
        else:
            user.equipment_context_expires_at = None
        await db.commit()
        items = ", ".join(tool_input["equipment"]) or "bodyweight only"
        return f"Equipment updated for {tool_input['context_note']}: {items}.", ui

    if tool_name == "restore_default_equipment":
        if user.default_equipment is not None:
            user.equipment = user.default_equipment
        user.equipment_context_note = None
        user.equipment_context_expires_at = None
        await db.commit()
        restored = ", ".join(user.equipment or []) or "none set"
        return f"Default equipment restored: {restored}.", ui

    if tool_name == "search_food":
        results = await usda_search_food(tool_input["query"])
        if not results:
            return f"No USDA data found for '{tool_input['query']}'. Estimate macros based on common values.", ui
        lines = []
        for r in results:
            p = r["per_100g"]
            lines.append(
                f"- {r['name']} ({r['data_type']}): "
                f"{p['calories']} kcal | {p['protein_g']}g protein | "
                f"{p['carbs_g']}g carbs | {p['fat_g']}g fat  (per 100g)"
            )
        return "USDA results:\n" + "\n".join(lines), ui

    if tool_name == "show_exercise_animation":
        exercise_data = await exercisedb_service.get_exercise(db, tool_input["exercise_name"])
        if exercise_data:
            ui.append(UIComponent(
                type="exercise_animation",
                data={**exercise_data, "coaching_cues": tool_input.get("coaching_cues", [])},
            ))
            return f"Showing animation for {tool_input['exercise_name']}.", ui
        return f"Animation not found for {tool_input['exercise_name']}.", ui

    if tool_name == "log_weight":
        log = WeightLog(
            user_id=user.id,
            weight_kg=tool_input["weight_kg"],
            notes=tool_input.get("notes"),
        )
        db.add(log)
        user.weight_kg = tool_input["weight_kg"]
        await db.commit()
        return f"Weight logged: {tool_input['weight_kg']} kg.", ui

    if tool_name == "get_weight_trend":
        since = datetime.utcnow() - timedelta(days=tool_input["period_days"])
        result = await db.execute(
            select(WeightLog)
            .where(WeightLog.user_id == user.id, WeightLog.logged_at >= since)
            .order_by(WeightLog.logged_at)
        )
        entries = result.scalars().all()
        if not entries:
            return "No weight data for this period.", ui
        data_points = [
            {"date": e.logged_at.strftime("%b %d"), "weight_kg": e.weight_kg}
            for e in entries
        ]
        change = round(entries[-1].weight_kg - entries[0].weight_kg, 1)
        ui.append(UIComponent(
            type="weight_trend_chart",
            data={
                "entries": data_points,
                "period_days": tool_input["period_days"],
                "start_weight": entries[0].weight_kg,
                "current_weight": entries[-1].weight_kg,
                "change_kg": change,
            },
        ))
        direction = "↓" if change < 0 else "↑"
        return (
            f"Weight over {tool_input['period_days']} days: "
            f"{entries[0].weight_kg} kg → {entries[-1].weight_kg} kg ({change:+.1f} kg {direction})."
        ), ui

    if tool_name == "schedule_reminder":
        from app.scheduler import add_reminder
        tz = user.timezone or "UTC"
        reminder = Reminder(
            user_id=user.id,
            label=tool_input["label"],
            message=tool_input["message"],
            days=tool_input["days"],
            hour=tool_input["hour"],
            minute=tool_input.get("minute", 0),
            timezone=tz,
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        add_reminder(reminder)
        days_str = ", ".join(tool_input["days"])
        time_str = f"{tool_input['hour']:02d}:{tool_input.get('minute', 0):02d}"
        return f"Reminder set: '{tool_input['label']}' — {days_str} at {time_str} ({tz}).", ui

    if tool_name == "list_reminders":
        result = await db.execute(
            select(Reminder)
            .where(Reminder.user_id == user.id, Reminder.is_active == True)
            .order_by(Reminder.created_at)
        )
        reminders = result.scalars().all()
        if not reminders:
            return "No active reminders.", ui
        lines = []
        for r in reminders:
            days_str = ", ".join(r.days)
            time_str = f"{r.hour:02d}:{r.minute:02d} {r.timezone}"
            lines.append(f"[{r.id[:8]}] {r.label}: {days_str} at {time_str}")
        return "Active reminders:\n" + "\n".join(lines), ui

    if tool_name == "cancel_reminder":
        from app.scheduler import remove_reminder
        result = await db.execute(
            select(Reminder).where(
                Reminder.id == tool_input["reminder_id"],
                Reminder.user_id == user.id,
            )
        )
        reminder = result.scalar_one_or_none()
        if not reminder:
            return "Reminder not found.", ui
        reminder.is_active = False
        await db.commit()
        remove_reminder(reminder.id)
        return f"Reminder '{reminder.label}' cancelled.", ui

    return f"Unknown tool: {tool_name}", ui
