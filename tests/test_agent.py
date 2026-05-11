from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.fitness_agent import run_agent
from app.agent.response_schema import CompoundResponse
from app.db.models import User


@pytest.fixture
def mock_user():
    return User(
        id="test-user-id",
        phone_number="+15551234567",
        name="Test User",
        fitness_level="intermediate",
        goals=["build muscle"],
        equipment=["barbell", "dumbbells"],
        onboarding_complete=True,
    )


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_run_agent_end_turn(mock_user, mock_db):
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [MagicMock(text="Great workout! Keep it up.", type="text")]

    with (
        patch("app.agent.fitness_agent.load_recent_messages", return_value=[]),
        patch("app.agent.fitness_agent.save_turn"),
        patch("app.agent.fitness_agent.maybe_compress_memory"),
        patch("app.agent.fitness_agent.anthropic.AsyncAnthropic") as mock_anthropic,
    ):
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        result = await run_agent("I finished my workout", mock_user, "web", mock_db)

    assert isinstance(result, CompoundResponse)
    assert result.text == "Great workout! Keep it up."
    assert result.ui_components == []


@pytest.mark.asyncio
async def test_run_agent_fallback_on_unknown_stop_reason(mock_user, mock_db):
    mock_response = MagicMock()
    mock_response.stop_reason = "max_tokens"
    mock_response.content = []

    with (
        patch("app.agent.fitness_agent.load_recent_messages", return_value=[]),
        patch("app.agent.fitness_agent.save_turn"),
        patch("app.agent.fitness_agent.maybe_compress_memory"),
        patch("app.agent.fitness_agent.anthropic.AsyncAnthropic") as mock_anthropic,
    ):
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        result = await run_agent("hello", mock_user, "web", mock_db)

    assert "couldn't process" in result.text
