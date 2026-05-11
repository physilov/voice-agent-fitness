import logging

import anthropic
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import ConversationMessage, User, WorkoutLog
from app.services.twilio_service import send_whatsapp_message
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MIN_HOURS_BETWEEN_CONTACTS = 12

_SYSTEM_PROMPT = """\
You are Apex, a proactive fitness coach doing a background check on a user.

Decide whether to send them a WhatsApp message right now, or do nothing.
Only reach out if there is a specific, genuinely useful reason. Be helpful, not annoying.

Good reasons to reach out:
- They have not logged a workout in 3+ days and have an active plan
- It has been 7+ days since any conversation
- They just hit a personal record in the last 24h worth acknowledging
- They missed 2+ consecutive scheduled training days
- They are on a strong streak and a short encouragement would help

Do NOT reach out if:
- They were contacted in the last 12 hours
- Everything looks on track with nothing specific to say
- It is outside 7am–9pm in their local timezone

You MUST call one of the two tools: send_whatsapp_message OR no_action.
"""

_PROACTIVE_TOOLS = [
    {
        "name": "send_whatsapp_message",
        "description": (
            "Send a proactive WhatsApp message to the user. "
            "Keep it under 3 sentences. Be personal and specific — reference their actual data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "no_action",
        "description": "Decide not to reach out to this user right now.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
            },
            "required": ["reason"],
        },
    },
]


async def _get_last_proactive_contact(user_id: str, db: AsyncSession) -> ConversationMessage | None:
    result = await db.execute(
        select(ConversationMessage)
        .where(
            ConversationMessage.user_id == user_id,
            ConversationMessage.channel == "proactive",
        )
        .order_by(desc(ConversationMessage.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _build_context(user: User, db: AsyncSession) -> str:
    now = datetime.utcnow()
    since_30d = now - timedelta(days=30)
    since_7d = now - timedelta(days=7)

    result = await db.execute(
        select(WorkoutLog)
        .where(WorkoutLog.user_id == user.id, WorkoutLog.logged_at >= since_30d)
        .order_by(desc(WorkoutLog.logged_at))
    )
    workouts = result.scalars().all()
    last_7d = sum(1 for w in workouts if w.logged_at >= since_7d)
    last_workout = workouts[0].logged_at.strftime("%A %Y-%m-%d") if workouts else "never"

    return (
        f"User: {user.name or 'Unknown'} | Timezone: {user.timezone or 'UTC'}\n"
        f"Goals: {', '.join(user.goals or []) or 'not set'}\n"
        f"Fitness level: {user.fitness_level or 'not set'}\n"
        f"Current UTC time: {now.strftime('%A %Y-%m-%d %H:%M')}\n\n"
        f"Workouts last 30 days: {len(workouts)} | last 7 days: {last_7d}\n"
        f"Most recent workout: {last_workout}\n\n"
        f"History / memory:\n{user.memory_summary or 'New user, no history yet.'}"
    )


async def run_proactive_check(user_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.phone_number:
        return

    # Restore expired equipment context before building user context
    if (
        user.equipment_context_expires_at
        and datetime.utcnow() >= user.equipment_context_expires_at
    ):
        if user.default_equipment is not None:
            user.equipment = user.default_equipment
        user.equipment_context_note = None
        user.equipment_context_expires_at = None
        await db.commit()

    last_contact = await _get_last_proactive_contact(user.id, db)
    if last_contact:
        hours_ago = (datetime.utcnow() - last_contact.created_at).total_seconds() / 3600
        if hours_ago < MIN_HOURS_BETWEEN_CONTACTS:
            return

    context = await _build_context(user, db)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        tools=_PROACTIVE_TOOLS,
        tool_choice={"type": "any"},  # force Claude to make a decision
        messages=[{"role": "user", "content": f"Review this user and decide:\n\n{context}"}],
    )

    for block in response.content:
        if block.type != "tool_use":
            continue
        if block.name == "send_whatsapp_message":
            msg = block.input["message"]
            await send_whatsapp_message(user.phone_number, msg)
            db.add(ConversationMessage(
                user_id=user.id, role="assistant", content=msg, channel="proactive"
            ))
            await db.commit()
            logger.info("Proactive message sent to user %s", user.id)
        elif block.name == "no_action":
            logger.debug("No action for user %s: %s", user.id, block.input.get("reason"))
        break
