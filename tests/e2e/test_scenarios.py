from pathlib import Path

import pytest
from sqlalchemy import select

from snabagent.agents import run_lot
from snabagent.db.models import AuditLog, Customer
from snabagent.db.repositories import LotRepo
from snabagent.db.session import AsyncSessionLocal

DATA = Path(__file__).resolve().parents[2] / "data" / "sample_tz"


async def _customer_id() -> str:
    async with AsyncSessionLocal() as s:
        c = (await s.execute(select(Customer).where(Customer.name == "SIBUR Demo"))).scalars().first()
        return str(c.id)  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_scenario_metal():
    raw = (DATA / "tz_metal_dirty.txt").read_text(encoding="utf-8")
    cust_id = await _customer_id()
    async with AsyncSessionLocal() as s:
        lot = await LotRepo(s).create({"customer_id": cust_id, "raw_request": raw, "phase": "pre_nmck"})
    final = await run_lot({
        "lot_id": str(lot.id),
        "customer_id": cust_id,
        "raw_request": raw,
        "phase": "pre_nmck",
        "status": "draft",
    })
    assert final.get("category") == "metals"
    assert final.get("report")
    async with AsyncSessionLocal() as s:
        events = list((await s.execute(select(AuditLog).where(AuditLog.lot_id == str(lot.id)))).scalars().all())
        agents = {e.agent_name for e in events}
    assert {"planner", "sourcer", "communicator", "verifier", "reporter"}.issubset(agents)


@pytest.mark.asyncio
async def test_scenario_it():
    raw = (DATA / "tz_it_dirty.txt").read_text(encoding="utf-8")
    cust_id = await _customer_id()
    async with AsyncSessionLocal() as s:
        lot = await LotRepo(s).create({"customer_id": cust_id, "raw_request": raw, "phase": "pre_nmck"})
    final = await run_lot({
        "lot_id": str(lot.id),
        "customer_id": cust_id,
        "raw_request": raw,
        "phase": "pre_nmck",
        "status": "draft",
    })
    assert final.get("category") == "it"


@pytest.mark.asyncio
async def test_scenario_chemistry():
    raw = (DATA / "tz_chemistry_dirty.txt").read_text(encoding="utf-8")
    cust_id = await _customer_id()
    async with AsyncSessionLocal() as s:
        lot = await LotRepo(s).create({"customer_id": cust_id, "raw_request": raw, "phase": "pre_nmck"})
    final = await run_lot({
        "lot_id": str(lot.id),
        "customer_id": cust_id,
        "raw_request": raw,
        "phase": "pre_nmck",
        "status": "draft",
    })
    assert final.get("category") == "chemistry"
