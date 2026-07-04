"""Тесты персистентной памяти (MemoryAgent): recall / writeback / boost."""

from __future__ import annotations

import pytest

from snabagent.db.repositories import CustomerRepo
from snabagent.db.session import AsyncSessionLocal
from snabagent.memory import apply_reliability_boost, recall, writeback
from snabagent.memory.store import get_or_create_profile, summarize_for_prompt


async def _new_customer(name: str) -> str:
    async with AsyncSessionLocal() as s:
        c = await CustomerRepo(s).get_or_create(name)
        return str(c.id)


@pytest.mark.asyncio
async def test_profile_created_with_defaults() -> None:
    cid = await _new_customer("MemTest Profile")
    profile = await get_or_create_profile(cid)
    assert profile["weight_price"] == 0.5
    assert profile["lots_processed"] == 0


@pytest.mark.asyncio
async def test_recall_empty_for_new_customer() -> None:
    cid = await _new_customer("MemTest Recall")
    mem = await recall(cid, "metals")
    assert mem["supplier_memory"] == {}
    assert mem["past_lots"] == []
    assert mem["profile"]["weight_price"] == 0.5


@pytest.mark.asyncio
async def test_writeback_then_recall_accumulates() -> None:
    cid = await _new_customer("MemTest Writeback")
    report = {
        "top_3": [{"inn": "7700000001", "supplier_name": "ООО Ромашка", "total_price": 100000}],
        "savings_vs_avg_pct": 9.5,
        "summary": "Выбран поставщик Ромашка",
    }
    verifications = [
        {"inn": "7700000001", "supplier_name": "ООО Ромашка", "confidence_score": 0.9, "lead_time_meets_spec": True},
        {"inn": "7700000002", "supplier_name": "ООО Лютик", "confidence_score": 0.6, "lead_time_meets_spec": False},
    ]
    await writeback(cid, category="metals", report=report, verifications=verifications, lot_id=None)

    mem = await recall(cid, "metals")
    assert "7700000001" in mem["supplier_memory"]
    winner = mem["supplier_memory"]["7700000001"]
    assert winner["times_selected"] == 1
    assert winner["times_seen"] == 1
    assert len(mem["past_lots"]) == 1
    assert mem["past_lots"][0]["chosen_supplier_inn"] == "7700000001"

    # второй лот — счётчики растут
    await writeback(cid, category="metals", report=report, verifications=verifications, lot_id=None)
    mem2 = await recall(cid, "metals")
    assert mem2["supplier_memory"]["7700000001"]["times_seen"] == 2
    assert mem2["profile"]["lots_processed"] == 2


def test_apply_reliability_boost_annotates_candidates() -> None:
    candidates = [{"inn": "111", "name": "A"}, {"inn": "222", "name": "B"}]
    supplier_memory = {"111": {"reliability_score": 0.83, "times_selected": 3}}
    out = apply_reliability_boost(candidates, supplier_memory)
    assert out[0]["memory_reliability"] == 0.83
    assert out[0]["memory_seen_before"] is True
    assert "memory_reliability" not in out[1]


def test_summarize_for_prompt_handles_empty() -> None:
    assert "пуста" in summarize_for_prompt({})
