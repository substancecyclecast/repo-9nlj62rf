"""CRUD tests for lots API."""
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
async def test_create_lot_pre_nmck(client):
    resp = await client.post("/api/v1/lots", json={
        "customer_name": "CRUD Test Co",
        "raw_request": "Болты М10 500 шт ГОСТ 7798",
        "phase": "pre_nmck",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("draft", "planned", "sourcing")


@pytest.mark.asyncio
async def test_create_lot_unregulated(client):
    resp = await client.post("/api/v1/lots", json={
        "customer_name": "Unreg Test",
        "raw_request": "Канцтовары для офиса",
        "phase": "unregulated",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_lot_with_budget(client):
    resp = await client.post("/api/v1/lots", json={
        "customer_name": "Budget Test",
        "raw_request": "Трубы стальные 108x4 1000м",
        "phase": "pre_nmck",
        "total_estimated_rub": 2500000,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_lots_page2(client):
    resp = await client.get("/api/v1/lots/", params={"page": 2, "page_size": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2


@pytest.mark.asyncio
async def test_list_lots_filter_draft(client):
    await client.post("/api/v1/lots", json={
        "customer_name": "Filter Test",
        "raw_request": "Цемент М500",
        "phase": "pre_nmck",
    })
    resp = await client.get("/api/v1/lots/", params={"status": "draft"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_lot_detail_and_audit(client):
    r = await client.post("/api/v1/lots", json={
        "customer_name": "Detail Audit",
        "raw_request": "Кабель ВВГнг 3x2.5 2000м",
        "phase": "pre_nmck",
    })
    lot_id = r.json()["id"]

    detail = await client.get(f"/api/v1/lots/{lot_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == lot_id

    audit = await client.get(f"/api/v1/lots/{lot_id}/audit")
    assert audit.status_code == 200


@pytest.mark.asyncio
async def test_approve_draft_lot(client):
    r = await client.post("/api/v1/lots", json={
        "customer_name": "Approve Draft",
        "raw_request": "Краска ПФ-115 500кг",
        "phase": "pre_nmck",
    })
    lot_id = r.json()["id"]
    resp = await client.post(f"/api/v1/lots/{lot_id}/approve", json={
        "reviewer_name": "Approver",
        "chosen_supplier": "sup-1",
    })
    assert resp.status_code in (200, 409)


@pytest.mark.asyncio
async def test_reject_draft_lot(client):
    r = await client.post("/api/v1/lots", json={
        "customer_name": "Reject Draft",
        "raw_request": "Гвозди 100мм 10кг",
        "phase": "pre_nmck",
    })
    lot_id = r.json()["id"]
    resp = await client.post(f"/api/v1/lots/{lot_id}/reject", json={
        "reviewer_name": "Rejector",
        "reason": "Тестовый отказ",
    })
    assert resp.status_code in (200, 409)
