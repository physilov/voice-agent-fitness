import anthropic
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.models import ConversationMessage, User

RECENT_MESSAGES_LIMIT = 20
SUMMARIZE_THRESHOLD = 40  # compress when total message count exceeds this


async def get_or_create_user(db: AsyncSession, phone_number: str) -> User:
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    user = result.scalar_one_or_none()
    if not user:
        user = User(phone_number=phone_number)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def load_recent_messages(db: AsyncSession, user_id: str) -> list[dict]:
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.user_id == user_id)
        .order_by(desc(ConversationMessage.created_at))
        .limit(RECENT_MESSAGES_LIMIT)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


async def save_turn(
    db: AsyncSession, user_id: str, user_text: str, assistant_text: str, channel: str
):
    db.add(ConversationMessage(user_id=user_id, role="user", content=user_text, channel=channel))
    db.add(
        ConversationMessage(
            user_id=user_id, role="assistant", content=assistant_text, channel=channel
        )
    )
    await db.commit()


async def maybe_compress_memory(db: AsyncSession, user: User):
    count_result = await db.execute(
        select(func.count())
        .select_from(ConversationMessage)
        .where(ConversationMessage.user_id == user.id)
    )
    if count_result.scalar() < SUMMARIZE_THRESHOLD:
        return

    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.user_id == user.id)
        .order_by(ConversationMessage.created_at)
    )
    all_messages = result.scalars().all()
    history = "\n".join(f"{m.role}: {m.content}" for m in all_messages)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": (
                "Summarize this fitness coaching conversation into a concise user profile update. "
                "Include: goals, current fitness level, workout preferences, notable progress, "
                "personal records, injuries or limitations, and motivational context.\n\n"
                f"{history}"
            ),
        }],
    )

    user.memory_summary = response.content[0].text
    for msg in all_messages[:-RECENT_MESSAGES_LIMIT]:
        await db.delete(msg)
    await db.commit()
