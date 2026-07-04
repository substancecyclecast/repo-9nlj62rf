"""Узлы памяти LangGraph (MemoryAgent).

* memory_recall     — первый узел графа: подтягивает профиль компании,
                      надёжность поставщиков и похожие прошлые лоты в state["memory"].
* memory_writeback  — последний узел: обновляет память по итогам лота
                      (самообучение). Ошибки памяти не роняют пайплайн.
"""

from __future__ import annotations

from typing import Any

from ..audit import write_audit
from ..memory import recall, writeback
from ..memory.store import summarize_for_prompt
from .state import LotState


async def memory_recall_node(state: LotState) -> dict[str, Any]:
    lot_id = state["lot_id"]
    customer_id = state.get("customer_id") or ""
    category = state.get("category")

    mem = await recall(customer_id, category)
    summary = summarize_for_prompt(mem)

    await write_audit(
        lot_id=lot_id,
        agent_name="memory",
        step_name="recall",
        input_payload={"customer_id": customer_id, "category": category},
        output_payload={
            "n_known_suppliers": len(mem.get("supplier_memory") or {}),
            "n_past_lots": len(mem.get("past_lots") or []),
            "profile": mem.get("profile"),
            "summary": summary,
        },
        decision="ok",
    )

    return {
        "memory": mem,
        "audit_events": [
            {
                "agent_name": "memory",
                "step_name": "recall",
                "decision": "ok",
                "n_known_suppliers": len(mem.get("supplier_memory") or {}),
                "n_past_lots": len(mem.get("past_lots") or []),
            }
        ],
    }


async def memory_writeback_node(state: LotState) -> dict[str, Any]:
    lot_id = state["lot_id"]
    customer_id = state.get("customer_id") or ""
    await writeback(
        customer_id,
        category=state.get("category"),
        report=state.get("report"),
        verifications=state.get("verifications") or [],
        lot_id=lot_id,
    )

    await write_audit(
        lot_id=lot_id,
        agent_name="memory",
        step_name="writeback",
        input_payload={"customer_id": customer_id},
        output_payload={"updated": True},
        decision="ok",
    )

    return {
        "audit_events": [{"agent_name": "memory", "step_name": "writeback", "decision": "ok"}],
    }
