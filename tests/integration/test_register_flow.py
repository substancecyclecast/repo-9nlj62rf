"""Integration tests for the registration flow."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from snabagent.api.main import app
from snabagent.api.main import limiter as app_limiter
from snabagent.api.routes.auth import limiter as auth_limiter


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Disable rate limiting for integration tests."""
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


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "testuser_reg@example.com",
        "password": "Str0ngP@ssword!",
        "full_name": "Test User",
        "company_name": "Test Company LLC",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "customer_id" in data
    assert data["email"] == "testuser_reg@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "email": "duplicate_test@example.com",
        "password": "Str0ngP@ssword!",
        "full_name": "Test User",
        "company_name": "Test Company",
    }
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 200
    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "weakpw@example.com",
        "password": "123",
        "full_name": "Test User",
        "company_name": "Test Company",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_fields(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_then_login(client):
    email = "flow_test@example.com"
    password = "Str0ngP@ssword!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Flow User",
        "company_name": "Flow Company",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
