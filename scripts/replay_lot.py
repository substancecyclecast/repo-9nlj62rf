"""Повторный прогон лота по lot_id. Используется в e2e."""
from __future__ import annotations

import asyncio
import sys

from snabagent.agents import run_lot
from snabagent.db.repositories import LotRepo
from snabagent.db.session import AsyncSessionLocal


async def main(lot_id: str):
    async with AsyncSessionLocal() as s:
        lot = await LotRepo(s).get(lot_id)
        if not lot:
            print("not found")
            return
        state = {
            "lot_id": str(lot.id),
            "customer_id": str(lot.customer_id),
            "raw_request": lot.raw_request,
            "phase": lot.phase.value if lot.phase else "pre_nmck",
            "status": "draft",
        }
    final = await run_lot(state)
    print({k: v for k, v in final.items() if k in ("status", "category", "requires_human")})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: replay_lot.py <lot_id>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
