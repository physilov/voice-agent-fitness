import anthropic
import base64
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.memory import load_recent_messages, maybe_compress_memory, save_turn
from app.agent.prompts import build_system_prompt
from app.agent.response_schema import CompoundResponse, UIComponent
from app.agent.tools import TOOL_DEFINITIONS, handle_tool_call
from app.config import settings
from app.db.models import User


async def _maybe_restore_equipment(user: User, db: AsyncSession) -> None:
    """Silently restore default equipment when a timed context has expired."""
    if not user.equipment_context_expires_at:
        return
    if datetime.utcnow() < user.equipment_context_expires_at:
        return
    if user.default_equipment is not None:
        user.equipment = user.default_equipment
    user.equipment_context_note = None
    user.equipment_context_expires_at = None
    await db.commit()


async def run_agent(
    user_text: str,
    user: User,
    channel: str,
    db: AsyncSession,
    image_data: bytes | None = None,
    image_media_type: str | None = None,
) -> CompoundResponse:
    await _maybe_restore_equipment(user, db)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    history = await load_recent_messages(db, user.id)

    if image_data and image_media_type:
        user_content: list | str = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type,
                    "data": base64.b64encode(image_data).decode(),
                },
            },
            {
                "type": "text",
                "text": user_text or "I sent a photo of my meal. Identify the foods and portions, look up their nutrition data, and log the meal for me.",
            },
        ]
    else:
        user_content = user_text

    messages = history + [{"role": "user", "content": user_content}]
    system_prompt = build_system_prompt(user, channel)
    all_ui: list[UIComponent] = []

    while True:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = next(
                (block.text for block in response.content if hasattr(block, "text")), ""
            )
            text_to_save = user_text or "[meal photo]"
            await save_turn(db, user.id, text_to_save, text, channel)
            await maybe_compress_memory(db, user)
            return CompoundResponse(text=text, ui_components=all_ui)

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
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
