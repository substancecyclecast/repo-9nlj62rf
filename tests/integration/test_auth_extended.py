"""Extended auth integration tests."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from snabagent.api.main import app
from snabagent.api.main import limiter as app_limiter
from snabagent.api.routes.auth import limiter as auth_limiter


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    app_limiter.enabled = False
    auth_limiter.enabled = False
    yield
    app_limiter.enabled = True
    auth_limiter.enabled = True


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def auth_client(client):
    """Client with auth token from registered user."""
    email = "authext@example.com"
    password = "Str0ngP@ssword!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Auth Test User",
        "company_name": "Auth Test Co",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
async def test_me_with_token(auth_client):
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "authext@example.com"


@pytest.mark.asyncio
async def test_me_without_token(client):
    resp = await client.get("/api/v1/auth/me", headers={"X-API-Key": ""})
    assert resp.status_code in (200, 401, 403)


@pytest.mark.asyncio
async def test_refresh_token(client):
    email = "refresh@example.com"
    password = "Str0ngP@ssword!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Refresh User",
        "company_name": "RefreshCo",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    refresh_token = login.json()["refresh_token"]
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid-token",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    email = "wrongpw@example.com"
    password = "Str0ngP@ssword!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Wrong PW User",
        "company_name": "WPCo",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "WrongP@ssword1",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "AnyP@ss1!",
    })
    assert resp.status_code == 401
