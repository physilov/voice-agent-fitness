from app.db.models import User

_TEMPLATE = """\
You are Apex, an expert fitness coach. Help users achieve their goals through \
personalized coaching, workout programming, and nutrition guidance.

## User Profile
Name: {name}
Age: {age} | Weight: {weight_kg}kg | Height: {height_cm}cm
Fitness Level: {fitness_level}
Goals: {goals}
{equipment_section}
Training days: {preferred_days}

## User Memory
{memory_summary}

## Instructions
- Reference the user's specific history and goals in every response.
- Use tools to log all data — never ask the user to track things manually.
- When explaining how to perform an exercise, always call show_exercise_animation.
- After logging any weighted set, call check_personal_record to detect PRs.
- If the user mentions traveling, camping, a hotel, or any change in location or
  available equipment, immediately call update_equipment_context.
- Channel: {channel}{voice_note}
"""

_VOICE_NOTE = "\n- VOICE CALL: Keep all responses under 2 sentences."


def _equipment_section(user: User) -> str:
    current = ", ".join(user.equipment or []) or "not specified"
    if not user.equipment_context_note:
        return f"Equipment: {current}"

    expires = ""
    if user.equipment_context_expires_at:
        expires = f" until {user.equipment_context_expires_at.strftime('%b %d')}"

    default = ", ".join(user.default_equipment or []) or "not specified"
    return (
        f"Equipment ({user.equipment_context_note}{expires}): {current}\n"
        f"Default equipment (home): {default}"
    )


def build_system_prompt(user: User, channel: str) -> str:
    return _TEMPLATE.format(
        name=user.name or "there",
        age=user.age or "?",
        weight_kg=user.weight_kg or "?",
        height_cm=user.height_cm or "?",
        fitness_level=user.fitness_level or "not set",
        goals=", ".join(user.goals or []) or "not set",
        equipment_section=_equipment_section(user),
        preferred_days=", ".join(user.preferred_days or []) or "not set",
        memory_summary=(
            user.memory_summary
            or "New user — gather their goals and fitness background early in the conversation."
        ),
        channel=channel,
        voice_note=_VOICE_NOTE if channel == "voice_call" else "",
    )
