from app.db.models import User

_TEMPLATE = """\
You are Apex, an expert AI fitness coach. Your purpose is to help {name} reach \
their fitness goals through personalized coaching, workout programming, and nutrition guidance.

## {name}'s Profile
{profile_section}

## Memory & History
{memory_summary}

Use your tools to take action — log workouts, search foods, generate plans, show exercises. \
Never ask the user to track things manually; use tools to do it for them.

When the profile is incomplete, gather what you need conversationally before creating \
plans that depend on it.

Channel: {channel}{voice_note}
"""

_VOICE_NOTE = "\n- VOICE CALL: Keep all responses under 2 sentences."


def _val(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, list):
        return ", ".join(v) if v else "—"
    return str(v)


def _equipment_section(user: User) -> str:
    current = _val(user.equipment)
    if not user.equipment_context_note:
        return f"Equipment: {current}"

    expires = ""
    if user.equipment_context_expires_at:
        expires = f" until {user.equipment_context_expires_at.strftime('%b %d')}"

    default = _val(user.default_equipment)
    return (
        f"Equipment ({user.equipment_context_note}{expires}): {current}\n"
        f"Default equipment (home): {default}"
    )


def _profile_section(user: User) -> str:
    lines = [
        f"Name: {_val(user.name)}",
        f"Age: {_val(user.age)} | Weight: {_val(user.weight_kg)}kg | Height: {_val(user.height_cm)}cm",
        f"Fitness Level: {_val(user.fitness_level)}",
        f"Goals: {_val(user.goals)}",
        _equipment_section(user),
        f"Training days: {_val(user.preferred_days)}",
    ]
    return "\n".join(lines)


def build_system_prompt(user: User, channel: str) -> str:
    return _TEMPLATE.format(
        name=user.name or "there",
        profile_section=_profile_section(user),
        memory_summary=(
            user.memory_summary
            or "New user — gather their goals and fitness background early in the conversation."
        ),
        channel=channel,
        voice_note=_VOICE_NOTE if channel == "voice_call" else "",
    )
