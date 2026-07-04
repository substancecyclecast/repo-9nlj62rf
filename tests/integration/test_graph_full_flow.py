import pytest
from sqlalchemy import select

from snabagent.agents import run_lot
from snabagent.db.models import Customer
from snabagent.db.repositories import LotRepo
from snabagent.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_full_pipeline_metal_scenario():
    async with AsyncSessionLocal() as s:
        customer = (await s.execute(select(Customer).where(Customer.name == "SIBUR Demo"))).scalars().first()
        assert customer is not None
        lot = await LotRepo(s).create(
            {
                "customer_id": customer.id,
                "raw_request": "Швеллер 14 ст3пс, 10 тонн; Арматура А500С 12, 5 тонн",
                "phase": "pre_nmck",
            }
        )
    state = {
        "lot_id": str(lot.id),
        "customer_id": str(customer.id),
        "raw_request": "Швеллер 14 ст3пс, 10 тонн; Арматура А500С 12, 5 тонн",
        "phase": "pre_nmck",
        "status": "draft",
    }
    final = await run_lot(state)
    assert final["status"] in ("report_ready", "verified")
    assert final.get("report")
    assert final["report"].get("top_3")
