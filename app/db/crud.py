from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> User | None:
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one_or_none()
