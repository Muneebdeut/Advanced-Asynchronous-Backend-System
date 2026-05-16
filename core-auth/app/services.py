from datetime import datetime, timezone

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_redis
from app.models import User
from app.schemas import UserCreate
from app.security import hash_password

_blacklist_prefix = "blacklist:"


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _remaining_ttl(token: str) -> int:
    payload = jwt.get_unverified_claims(token)
    exp = payload.get("exp", 0)
    remaining = exp - int(datetime.now(tz=timezone.utc).timestamp())
    return max(remaining, 0)


async def blacklist_token(token: str) -> None:
    ttl = _remaining_ttl(token)
    if ttl > 0:
        await get_redis().setex(f"{_blacklist_prefix}{token}", ttl, "1")


async def is_blacklisted(token: str) -> bool:
    return await get_redis().exists(f"{_blacklist_prefix}{token}") == 1
