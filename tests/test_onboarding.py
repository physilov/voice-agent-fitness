from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.onboarding_agent import run_onboarding
from app.db.models import User


@pytest.fixture
def new_user():
    return User(
        id="user-new",
        phone_number="+15559990000",
        onboarding_complete=False,
    )


def _make_text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def _make_tool_response(tool_name: str, tool_input: dict, tool_id: str = "t1"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_id
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response


# ── run_onboarding ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_onboarding_collects_name_and_returns_question(new_user):
    db = AsyncMock()
    db.commit = AsyncMock()

    with patch("app.agent.onboarding_agent.anthropic.AsyncAnthropic") as mock_cls, \
         patch("app.agent.onboarding_agent.load_recent_messages", return_value=[]), \
         patch("app.agent.onboarding_agent.save_turn", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(
            return_value=_make_text_response("Great to meet you! What's your main fitness goal?")
        )

        response = await run_onboarding("I'm Alex", new_user, "web", db)

    assert response.text != ""
    assert new_user.onboarding_complete is False  # not done yet


@pytest.mark.asyncio
async def test_complete_onboarding_sets_flag(new_user):
    db = AsyncMock()
    db.commit = AsyncMock()

    complete_response = _make_tool_response("complete_onboarding", {}, "t-complete")
    final_text_response = _make_text_response("You're all set! Let's crush your goals.")

    call_count = 0

    async def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return complete_response
        return final_text_response

    with patch("app.agent.onboarding_agent.anthropic.AsyncAnthropic") as mock_cls, \
         patch("app.agent.onboarding_agent.load_recent_messages", return_value=[]), \
         patch("app.agent.onboarding_agent.save_turn", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(side_effect=side_effect)

        response = await run_onboarding("I'm ready!", new_user, "web", db)

    assert new_user.onboarding_complete is True
    db.commit.assert_called()
    assert "set" in response.text.lower() or "goals" in response.text.lower()


@pytest.mark.asyncio
async def test_onboarding_calls_update_user_profile(new_user):
    db = AsyncMock()
    db.commit = AsyncMock()

    profile_response = _make_tool_response(
        "update_user_profile", {"name": "Alex", "fitness_level": "beginner"}, "t-profile"
    )
    follow_up_response = _make_text_response("What equipment do you have?")

    call_count = 0

    async def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return profile_response
        return follow_up_response

    with patch("app.agent.onboarding_agent.anthropic.AsyncAnthropic") as mock_cls, \
         patch("app.agent.onboarding_agent.load_recent_messages", return_value=[]), \
         patch("app.agent.onboarding_agent.save_turn", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(side_effect=side_effect)

        await run_onboarding("My name is Alex and I'm a beginner", new_user, "web", db)

    assert new_user.name == "Alex"
    assert new_user.fitness_level == "beginner"


@pytest.mark.asyncio
async def test_onboarding_voice_brevity_note(new_user):
    db = AsyncMock()
    db.commit = AsyncMock()

    captured_prompts = []

    async def capture(**kwargs):
        captured_prompts.append(kwargs.get("system", ""))
        return _make_text_response("What's your goal?")

    with patch("app.agent.onboarding_agent.anthropic.AsyncAnthropic") as mock_cls, \
         patch("app.agent.onboarding_agent.load_recent_messages", return_value=[]), \
         patch("app.agent.onboarding_agent.save_turn", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(side_effect=capture)

        await run_onboarding("Hello", new_user, "voice_call", db)

    assert captured_prompts
    assert "VOICE CALL" in captured_prompts[0]
