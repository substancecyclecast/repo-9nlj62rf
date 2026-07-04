import pytest
from sqlalchemy import select

from snabagent.agents.planner import planner_node
from snabagent.db.models import Customer
from snabagent.db.repositories import LotRepo
from snabagent.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_planner_maps_metal_request():
    async with AsyncSessionLocal() as s:
        customer = (await s.execute(select(Customer).where(Customer.name == "SIBUR Demo"))).scalars().first()
        assert customer is not None
        lot = await LotRepo(s).create(
            {
                "customer_id": customer.id,
                "raw_request": "Швеллер 14-й, трешка, 10 тонн надо",
                "phase": "pre_nmck",
            }
        )
    state = {
        "lot_id": str(lot.id),
        "customer_id": str(customer.id),
        "raw_request": "Швеллер 14-й, трешка, 10 тонн надо",
        "phase": "pre_nmck",
        "status": "draft",
    }
    out = await planner_node(state)
    items = out["parsed_items"]
    assert items
    # Хотя бы одна позиция должна быть смаппирована именно на швеллер
    assert any("MET-SHV-14" in (i.get("matched_nsi_sku") or "") for i in items)
