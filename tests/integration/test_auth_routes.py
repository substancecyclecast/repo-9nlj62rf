"""Integration: проверка multi-tenant авторизации (JWT + RBAC)."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from snabagent.api.main import app
from snabagent.api.security import hash_password
from snabagent.db.models import Base, Customer, User, UserRole
from snabagent.db.session import AsyncSessionLocal, engine


@pytest.fixture(scope="function")
async def _users():
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as s:
        existing_email = (
            await s.execute(select(User).where(User.email == "auth_admin@test.local"))
        ).scalars().first()
        if existing_email:
            yield
            return
        c = (
            await s.execute(select(Customer).where(Customer.name == "TestCorp Auth"))
        ).scalars().first()
        if c is None:
            c = Customer(name="TestCorp Auth")
            s.add(c)
            await s.commit()
            await s.refresh(c)
        s.add_all([
            User(
                customer_id=c.id,
                email="auth_admin@test.local",
                hashed_password=hash_password("adminpw"),
                role=UserRole.admin,
            ),
            User(
                customer_id=c.id,
                email="auth_buyer@test.local",
                hashed_password=hash_password("buyerpw"),
                role=UserRole.buyer,
                approval_limit_rub=1_000_000.0,
            ),
            User(
                customer_id=c.id,
                email="auth_viewer@test.local",
                hashed_password=hash_password("viewerpw"),
                role=UserRole.viewer,
            ),
        ])
        await s.commit()
    yield


@pytest.mark.asyncio
async def test_login_returns_jwt(_users):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "auth_admin@test.local", "password": "adminpw"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert body["role"] == "admin"
    assert body["email"] == "auth_admin@test.local"


@pytest.mark.asyncio
async def test_login_wrong_password_401(_users):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "auth_admin@test.local", "password": "WRONG"},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_jwt_me_returns_user(_users):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "auth_buyer@test.local", "password": "buyerpw"},
        )
        token = r.json()["access_token"]
        r2 = await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["role"] == "buyer"
    assert body["approval_limit_rub"] == 1_000_000.0
