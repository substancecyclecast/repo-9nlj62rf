"""Extended integration tests for lots API."""
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
async def test_create_lot(client):
    resp = await client.post("/api/v1/lots", json={
        "customer_name": "Ext Test",
        "raw_request": "Болты М10 500 шт ГОСТ",
        "phase": "pre_nmck",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] in ("draft", "planned", "sourcing")


@pytest.mark.asyncio
async def test_list_lots_pagination(client):
    resp = await client.get("/api/v1/lots/", params={"page": 1, "page_size": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "pages" in data
    assert data["page"] == 1
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_lot_detail(client):
    r = await client.post("/api/v1/lots", json={
        "customer_name": "Detail Test",
        "raw_request": "Арматура А500",
        "phase": "pre_nmck",
    })
    lot_id = r.json()["id"]
    resp = await client.get(f"/api/v1/lots/{lot_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == lot_id


@pytest.mark.asyncio
async def test_lot_audit(client):
    r = await client.post("/api/v1/lots", json={
        "customer_name": "Audit Test",
        "raw_request": "Цемент М500",
        "phase": "pre_nmck",
    })
    lot_id = r.json()["id"]
    resp = await client.get(f"/api/v1/lots/{lot_id}/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_approve_lot(client):
    r = await client.post("/api/v1/lots", json={
        "customer_name": "Approve Test",
        "raw_request": "Кабель ВВГ",
        "phase": "pre_nmck",
    })
    lot_id = r.json()["id"]
    resp = await client.post(f"/api/v1/lots/{lot_id}/approve", json={
        "reviewer_name": "Test",
        "chosen_supplier": "supplier-1",
    })
    assert resp.status_code in (200, 409)


@pytest.mark.asyncio
async def test_lot_not_found(client):
    resp = await client.get("/api/v1/lots/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_csv(client):
    resp = await client.get("/api/v1/export/lots.csv")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_export_jsonl(client):
    resp = await client.get("/api/v1/export/lots.jsonl")
    assert resp.status_code == 200
