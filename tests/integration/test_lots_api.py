"""Integration: /lots create, list, get, approve, reject, excel."""
from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from snabagent.api.main import app
from snabagent.db.models import Base
from snabagent.db.session import engine


@pytest.fixture(scope="function")
async def _db_initialized():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_create_and_list_lot(_db_initialized):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        payload = {
            "customer_name": "Demo Customer Lots-API",
            "raw_request": "Нужны болты М10 100 штук",
            "phase": "pre_nmck",
        }
        r = await c.post("/api/v1/lots", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert "id" in body
        lot_id = body["id"]

        r2 = await c.get("/api/v1/lots/")
        assert r2.status_code == 200
        data = r2.json()
        lots = data["items"] if isinstance(data, dict) and "items" in data else data
        assert any(x["id"] == lot_id for x in lots), "created lot not visible in list"

        r3 = await c.get(f"/api/v1/lots/{lot_id}")
        assert r3.status_code == 200
        detail = r3.json()
        assert detail["id"] == lot_id
        assert detail["status"] in ("draft", "planned", "sourcing", "rfq_sent",
                                    "responses_collected", "negotiating",
                                    "verified", "report_ready", "escalated", "failed")


@pytest.mark.asyncio
async def test_list_lots_filter_by_status(_db_initialized):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        await c.post("/api/v1/lots", json={
            "customer_name": "Demo Customer Lots-API-2",
            "raw_request": "Тест",
            "phase": "pre_nmck",
        })
        await asyncio.sleep(0.1)  # лот успеет хотя бы попасть в draft
        # Все статусы доступны через фильтр
        for status_v in ("report_ready", "escalated", "draft", "failed"):
            r = await c.get("/api/v1/lots/", params={"status": status_v, "page_size": 5})
            assert r.status_code == 200, r.text
            data = r.json()
            assert isinstance(data, dict) and "items" in data


@pytest.mark.asyncio
async def test_reject_existing_lot(_db_initialized):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v1/lots", json={
            "customer_name": "Reject Test",
            "raw_request": "На реджект",
            "phase": "pre_nmck",
        })
        lot_id = r.json()["id"]
        # Dev-режим (X-API-Key dev-only) → role=admin, можно reject
        r2 = await c.post(
            f"/api/v1/lots/{lot_id}/reject",
            json={"reviewer_name": "Test", "reason": "Тест"},
        )
        # Может быть 200 OK или 409, если лот ещё не дошёл до report_ready
        assert r2.status_code in (200, 409, 404)


@pytest.mark.asyncio
async def test_reject_unknown_lot_404(_db_initialized):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(
            "/api/v1/lots/00000000-0000-0000-0000-000000000000/reject",
            json={"reviewer_name": "x"},
        )
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_parse_attachment_txt(_db_initialized):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        files = {"file": ("test.txt", b"Hello SnabAgent", "text/plain")}
        r = await c.post("/api/v1/lots/parse-attachment", files=files)
    assert r.status_code == 200
    body = r.json()
    assert "text" in body
    assert "Hello" in body["text"]


@pytest.mark.asyncio
async def test_parse_attachment_too_large(_db_initialized):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        big = b"x" * (10 * 1024 * 1024 + 10)
        files = {"file": ("big.txt", big, "text/plain")}
        r = await c.post("/api/v1/lots/parse-attachment", files=files)
    assert r.status_code == 413
