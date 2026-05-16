from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import create_app

TEST_DB = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DB, echo=False)
Session = async_sessionmaker(bind=engine, expire_on_commit=False)


class FakeRedis:
    def __init__(self):
        self._keys: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str):
        self._keys[key] = value

    async def exists(self, key: str) -> int:
        return 1 if key in self._keys else 0

    async def ping(self) -> bool:
        return True

    async def aclose(self):
        self._keys.clear()


async def override_db() -> AsyncGenerator[AsyncSession, None]:
    async with Session() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
def fake_redis():
    return FakeRedis()


@pytest_asyncio.fixture
async def client(fake_redis) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_db] = override_db

    with (
        patch("app.services.get_redis", return_value=fake_redis),
        patch("app.routes.get_redis", return_value=fake_redis),
        patch("app.database.init_redis", new_callable=AsyncMock),
        patch("app.database.close_redis", new_callable=AsyncMock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
