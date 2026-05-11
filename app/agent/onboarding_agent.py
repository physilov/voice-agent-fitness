import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.memory import load_recent_messages, save_turn
from app.agent.response_schema import CompoundResponse, UIComponent
from app.agent.tools import TOOL_DEFINITIONS, handle_tool_call
from app.config import settings
from app.db.models import User

_ONBOARDING_SYSTEM_PROMPT = """\
You are Apex, an expert fitness coach welcoming a brand-new user for the first time.

Your only goal in this conversation is to collect enough information to:
1. Build a clear picture of who this person is and what they want.
2. Generate a personalized workout plan tailored to them.
3. Mark onboarding as complete.

## What to collect (in a natural, friendly conversation):
- First name
- Primary fitness goal (e.g. lose weight, build muscle, run a 5K, stay active)
- Current fitness level (beginner / intermediate / advanced)
- Available equipment (home gym, dumbbells, bodyweight only, full gym, etc.)
- Preferred training days per week (2–6)
- Any injuries or physical limitations
- Age and weight (optional but helpful for programming)

## Rules:
- Ask 1–2 questions at a time — never overwhelm with a list.
- Be warm, energetic, and encouraging.
- Call `update_user_profile` as soon as you have each piece of information.
- Once you know their goal, level, equipment, and days/week, call `generate_workout_plan`.
- After generating the plan, immediately call `complete_onboarding`.
- Do NOT proceed to general coaching until `complete_onboarding` is called.
- Channel: {channel}{voice_note}
"""

_VOICE_NOTE = "\n- VOICE CALL: Keep all responses under 2 sentences."

_COMPLETE_ONBOARDING_TOOL = {
    "name": "complete_onboarding",
    "description": (
        "Mark onboarding as complete. Call this immediately after generating the first workout plan. "
        "This unlocks the full coaching experience for the user."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

_ONBOARDING_TOOLS = TOOL_DEFINITIONS + [_COMPLETE_ONBOARDING_TOOL]


async def run_onboarding(
    user_text: str,
    user: User,
    channel: str,
    db: AsyncSession,
) -> CompoundResponse:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    history = await load_recent_messages(db, user.id)
    messages = history + [{"role": "user", "content": user_text}]
    voice_note = _VOICE_NOTE if channel == "voice_call" else ""
    system_prompt = _ONBOARDING_SYSTEM_PROMPT.format(channel=channel, voice_note=voice_note)
    all_ui: list[UIComponent] = []

    while True:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=system_prompt,
            tools=_ONBOARDING_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = next(
                (block.text for block in response.content if hasattr(block, "text")), ""
            )
            await save_turn(db, user.id, user_text, text, channel)
            return CompoundResponse(text=text, ui_components=all_ui)

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if block.name == "complete_onboarding":
                    user.onboarding_complete = True
                    await db.commit()
                    result_text = "Onboarding complete. Welcome to Apex!"
                    ui_components: list[UIComponent] = []
                else:
                    result_text, ui_components = await handle_tool_call(
                        block.name, block.input, user, db
                    )

                all_ui.extend(ui_components)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

            messages = messages + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results},
            ]
            continue

        break

    return CompoundResponse(text="I couldn't process that request. Please try again.")
