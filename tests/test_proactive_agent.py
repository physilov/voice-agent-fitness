from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.proactive_agent import MIN_HOURS_BETWEEN_CONTACTS, run_proactive_check
from app.db.models import ConversationMessage, User


@pytest.fixture
def user():
    return User(
        id="user-123",
        phone_number="+15551234567",
        name="Alex",
        fitness_level="intermediate",
        goals=["build muscle"],
        timezone="UTC",
    )


def _db_returning(value):
    """Build an AsyncMock DB whose execute().scalar_one_or_none() returns value."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.mark.asyncio
async def test_skips_recently_contacted_user(mocker, user):
    db = _db_returning(user)

    recent = MagicMock(spec=ConversationMessage)
    recent.created_at = datetime.utcnow() - timedelta(hours=MIN_HOURS_BETWEEN_CONTACTS - 1)
    mocker.patch(
        "app.agent.proactive_agent._get_last_proactive_contact",
        new=AsyncMock(return_value=recent),
    )

    mock_claude = mocker.patch("app.agent.proactive_agent.anthropic.AsyncAnthropic")
    await run_proactive_check(user.id, db)

    mock_claude.assert_not_called()


@pytest.mark.asyncio
async def test_sends_message_on_tool_call(mocker, user):
    db = _db_returning(user)
    db.add = MagicMock()
    db.commit = AsyncMock()

    mocker.patch(
        "app.agent.proactive_agent._get_last_proactive_contact",
        new=AsyncMock(return_value=None),
    )
    mocker.patch(
        "app.agent.proactive_agent._build_context",
        new=AsyncMock(return_value="user context text"),
    )

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "send_whatsapp_message"
    tool_block.input = {"message": "Hey Alex, time to train!"}
    mock_response = MagicMock(content=[tool_block])

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    mocker.patch("app.agent.proactive_agent.anthropic.AsyncAnthropic", return_value=mock_client)

    mock_send = mocker.patch(
        "app.agent.proactive_agent.send_whatsapp_message", new=AsyncMock()
    )

    await run_proactive_check(user.id, db)

    mock_send.assert_called_once_with(user.phone_number, "Hey Alex, time to train!")
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_no_message_on_no_action(mocker, user):
    db = _db_returning(user)
    db.add = MagicMock()

    mocker.patch(
        "app.agent.proactive_agent._get_last_proactive_contact",
        new=AsyncMock(return_value=None),
    )
    mocker.patch(
        "app.agent.proactive_agent._build_context",
        new=AsyncMock(return_value="user context text"),
    )

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "no_action"
    tool_block.input = {"reason": "User is on track"}
    mock_response = MagicMock(content=[tool_block])

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    mocker.patch("app.agent.proactive_agent.anthropic.AsyncAnthropic", return_value=mock_client)

    mock_send = mocker.patch(
        "app.agent.proactive_agent.send_whatsapp_message", new=AsyncMock()
    )

    await run_proactive_check(user.id, db)

    mock_send.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_skips_user_with_no_phone(mocker):
    user_no_phone = User(id="user-456", phone_number=None)
    db = _db_returning(user_no_phone)

    mock_claude = mocker.patch("app.agent.proactive_agent.anthropic.AsyncAnthropic")
    await run_proactive_check(user_no_phone.id, db)

    mock_claude.assert_not_called()
