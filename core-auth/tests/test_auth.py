import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.config import Settings

BASE = "/api/v1/auth"
EMAIL = "test@example.com"
PASSWORD = "Str0ng!Pass#2024"
tokens: dict = {}


def test_settings_reject_weak_secrets():
    with pytest.raises(ValidationError):
        Settings(
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
            REDIS_URL="redis://localhost:6379/0",
            ACCESS_TOKEN_SECRET="short",
            REFRESH_TOKEN_SECRET="also-too-short-for-validation",
            APP_ENV="development",
        )


def test_settings_reject_placeholder_in_production():
    with pytest.raises(ValidationError):
        Settings(
            DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
            REDIS_URL="redis://localhost:6379/0",
            ACCESS_TOKEN_SECRET="CHANGE_ME_ACCESS_SECRET_32_CHARS_MIN",
            REFRESH_TOKEN_SECRET="CHANGE_ME_REFRESH_SECRET_32_CHARS_MIN",
            APP_ENV="production",
        )


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    r = await client.post(f"{BASE}/register", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == EMAIL
    assert body["is_active"] is True
    assert "password" not in body


@pytest.mark.asyncio
async def test_weak_password(client: AsyncClient):
    r = await client.post(f"{BASE}/register", json={"email": "a@b.com", "password": "short"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_email(client: AsyncClient):
    r = await client.post(f"{BASE}/register", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    r = await client.post(f"{BASE}/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] != body["refresh_token"]
    tokens["access"] = body["access_token"]
    tokens["refresh"] = body["refresh_token"]


@pytest.mark.asyncio
async def test_wrong_password(client: AsyncClient):
    r = await client.post(f"{BASE}/login", json={"email": EMAIL, "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    r = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {tokens['access']}"})
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    r = await client.get(f"{BASE}/me")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_refresh(client: AsyncClient):
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": tokens["refresh"]})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] != tokens["access"]
    tokens["access"] = body["access_token"]
    tokens["refresh"] = body["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client: AsyncClient):
    r = await client.post(f"{BASE}/refresh", json={"refresh_token": tokens["access"]})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    r = await client.post(f"{BASE}/logout", headers={"Authorization": f"Bearer {tokens['access']}"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_revoked_token(client: AsyncClient):
    r = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {tokens['access']}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
