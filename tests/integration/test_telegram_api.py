"""Integration tests for telegram webhook endpoint."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from snabagent.api.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.asyncio
async def test_telegram_start_command(client):
    resp = await client.post("/api/v1/webhooks/telegram", json={
        "message": {
            "chat": {"id": 12345},
            "text": "/start",
        },
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_telegram_help_command(client):
    resp = await client.post("/api/v1/webhooks/telegram", json={
        "message": {
            "chat": {"id": 12345},
            "text": "/help",
        },
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_telegram_new_command(client):
    resp = await client.post("/api/v1/webhooks/telegram", json={
        "message": {
            "chat": {"id": 12345},
            "text": "/new Нужны болты М10 100 шт",
        },
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_telegram_status_command(client):
    resp = await client.post("/api/v1/webhooks/telegram", json={
        "message": {
            "chat": {"id": 12345},
            "text": "/status",
        },
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_telegram_empty_body(client):
    resp = await client.post("/api/v1/webhooks/telegram", json={})
    assert resp.status_code == 200
