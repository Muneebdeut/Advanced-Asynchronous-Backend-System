import logging
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

redis_pool: aioredis.Redis | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_redis() -> None:
    global redis_pool
    redis_pool = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        await redis_pool.ping()
    except Exception as exc:
        if settings.APP_ENV.lower() in ("development", "test"):
            logger.warning("Redis unavailable (%s); using in-memory fallback", exc)
            await redis_pool.aclose()
            import fakeredis.aioredis

            redis_pool = fakeredis.aioredis.FakeRedis(encoding="utf-8", decode_responses=True)
        else:
            raise


async def close_redis() -> None:
    global redis_pool
    if redis_pool is not None:
        await redis_pool.aclose()
        redis_pool = None


def get_redis() -> aioredis.Redis:
    if redis_pool is None:
        raise RuntimeError("Redis is not initialised")
    return redis_pool
