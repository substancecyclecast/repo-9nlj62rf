"""Полностью оффлайн-демо: SQLite + FakeLLM + Fake-embeddings.

Запускает все 3 сценария (metals/it/chemistry) последовательно и выводит JSON-отчёт.
Если есть aiosqlite — БД создаётся локально, иначе использует переменную окружения.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Принудительно переводим окружение в оффлайн-режим
os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("LLM_PRIMARY", "fake")
os.environ.setdefault("LLM_FALLBACK", "fake")
os.environ.setdefault("LLM_VERIFIER", "fake")
os.environ.setdefault("EMBEDDING_BACKEND", "fake")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./snabagent_offline_demo.db")
os.environ.setdefault("DEMO_MODE", "true")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snabagent.agents import run_lot  # noqa: E402
from snabagent.db.models import Base  # noqa: E402
from snabagent.db.repositories import CustomerRepo, LotRepo  # noqa: E402
from snabagent.db.seed import seed_all  # noqa: E402
from snabagent.db.session import AsyncSessionLocal, engine  # noqa: E402
from snabagent.vector.nsi_index import reindex_nsi  # noqa: E402
from snabagent.vector.supplier_index import reindex_suppliers  # noqa: E402

SCENARIOS = [
    ("metals", "tz_metal_dirty.txt", "pre_nmck"),
    ("it", "tz_it_dirty.txt", "pre_nmck"),
    ("chemistry", "tz_chemistry_dirty.txt", "pre_nmck"),
]


async def _aiosqlite_available() -> bool:
    try:
        import aiosqlite  # noqa: F401
        return True
    except ImportError:
        return False


async def main():
    if not await _aiosqlite_available():
        print("WARNING: aiosqlite не установлен, оффлайн-демо требует его. pip install aiosqlite")
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_all()
    n = await reindex_nsi()
    m = await reindex_suppliers()
    print(f"Seed: NSI={n} suppliers={m}")

    async with AsyncSessionLocal() as s:
        customer = await CustomerRepo(s).get_or_create("SIBUR Demo")

    results: list[dict] = []
    for label, fname, phase in SCENARIOS:
        path = ROOT / "data" / "sample_tz" / fname
        raw = path.read_text(encoding="utf-8")
        async with AsyncSessionLocal() as s:
            lot = await LotRepo(s).create(
                {"customer_id": customer.id, "raw_request": raw, "phase": phase}
            )
        state = {
            "lot_id": str(lot.id),
            "customer_id": str(customer.id),
            "raw_request": raw,
            "phase": phase,
            "status": "draft",
        }
        final = await run_lot(state)
        results.append(
            {
                "scenario": label,
                "lot_id": str(lot.id),
                "status": final.get("status"),
                "category": final.get("category"),
                "n_items": len(final.get("parsed_items") or []),
                "n_suppliers": len(final.get("suppliers") or []),
                "n_responses": len(final.get("responses_collected") or []),
                "n_verifications": len(final.get("verifications") or []),
                "top_3": (final.get("report") or {}).get("top_3"),
                "savings_pct": (final.get("report") or {}).get("savings_vs_avg_pct"),
                "requires_human": final.get("requires_human"),
                "escalation_reason": final.get("escalation_reason"),
            }
        )

    out = ROOT / "data" / "offline_demo_results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== Offline demo results ===")
    for r in results:
        print(
            f"- [{r['scenario']}] status={r['status']} items={r['n_items']} suppliers={r['n_suppliers']} "
            f"responses={r['n_responses']} verifications={r['n_verifications']} savings={r.get('savings_pct')}%"
        )
    print(f"Подробный JSON: {out}")


if __name__ == "__main__":
    asyncio.run(main())
