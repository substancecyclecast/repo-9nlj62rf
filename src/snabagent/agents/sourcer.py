"""Sourcer — собирает кандидатов поставщиков из трёх источников и ранкирует через LLM."""

from __future__ import annotations

import json
from typing import Any

from ..audit import write_audit
from ..llm.router import complete_with_fallback
from ..memory.store import apply_reliability_boost
from ..settings import settings
from ..vector import qdrant_client
from ..vector.embeddings import embed_queries
from . import prompts
from .state import LotState
from .tools.historical import lookup_by_skus
from .tools.spark_mock import CATEGORY_TO_OKVED, search_by_okved


async def _vector_search_suppliers(query: str, top_k: int = 10) -> list[dict]:
    vec = embed_queries([query])[0]
    res = await qdrant_client.search(settings.qdrant_suppliers_collection, vec, limit=top_k)
    out = []
    for r in res:
        p = r["payload"]
        out.append(
            {
                "supplier_id": p.get("supplier_id"),
                "inn": p.get("inn"),
                "name": p.get("name"),
                "contact_email": p.get("contact_email"),
                "website": p.get("website"),
                "region": p.get("region"),
                "categories": p.get("categories") or [],
                "historical_score": p.get("historical_score"),
                "source": "vector",
                "reasoning": f"Семантическое сходство со списком категорий ({r['score']:.2f})",
            }
        )
    return out


async def sourcer_node(state: LotState) -> dict[str, Any]:
    lot_id = state["lot_id"]
    items = state.get("parsed_items") or []
    category = state.get("category") or "mro"
    customer_id = state.get("customer_id") or ""

    skus = [i["matched_nsi_sku"] for i in items if i.get("matched_nsi_sku")]

    hist = await lookup_by_skus(customer_id, skus) if skus else []
    qd_query = " | ".join(i.get("matched_nsi_name") or i.get("raw_phrase", "") for i in items)
    vec = await _vector_search_suppliers(f"Поставщики категории {category}: {qd_query}", top_k=10)
    spark = await search_by_okved(CATEGORY_TO_OKVED.get(category, []))

    # Дедуп по ИНН
    seen: dict[str, dict] = {}
    for c in hist + vec + spark:
        inn = c.get("inn")
        if not inn:
            continue
        if inn in seen:
            old = seen[inn]
            # «historical» побеждает остальные источники
            old_source_rank = {"historical": 0, "vector": 1, "spark": 2}.get(old.get("source", "spark"), 2)
            new_source_rank = {"historical": 0, "vector": 1, "spark": 2}.get(c.get("source", "spark"), 2)
            if new_source_rank < old_source_rank:
                seen[inn] = c
            continue
        seen[inn] = c
    candidates = list(seen.values())[:30]

    # MemoryAgent: подмешиваем накопленную надёжность поставщиков из памяти,
    # чтобы LLM-ранкер учитывал прошлый опыт работы с ними.
    memory = state.get("memory") or {}
    supplier_memory = memory.get("supplier_memory") or {}
    candidates = apply_reliability_boost(candidates, supplier_memory)
    n_with_memory = sum(1 for c in candidates if c.get("memory_seen_before"))

    # LLM-ранжирование
    system = (
        "Ты — ранкер поставщиков, возвращай валидный JSON. "
        "Если у кандидата есть memory_reliability — это накопленный опыт работы с ним; "
        "при прочих равных предпочитай проверенных поставщиков с высоким скором."
    )
    user = prompts.render(
        "sourcer_user.j2",
        candidates_json=json.dumps(candidates, ensure_ascii=False),
        top_k=6,
    )
    resp = await complete_with_fallback(system, user, json_schema={"type": "object"})
    try:
        ranked = json.loads(resp.text).get("suppliers", [])
    except json.JSONDecodeError:
        ranked = candidates[:6]

    await write_audit(
        lot_id=lot_id,
        agent_name="sourcer",
        step_name="rank_suppliers",
        input_payload={
            "candidates_n": len(candidates),
            "sources": {
                "historical": len(hist),
                "vector": len(vec),
                "spark": len(spark),
            },
            "candidates_with_memory": n_with_memory,
        },
        output_payload={"top": ranked[:6]},
        prompt_text=user[:3000],
        llm_response_raw=resp.raw,
        model_name=resp.model_name,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        latency_ms=resp.latency_ms,
        confidence=0.85,
        decision="ok",
    )

    return {
        "suppliers": ranked[:6],
        "status": "sourcing",
        "audit_events": [
            {
                "agent_name": "sourcer",
                "step_name": "rank_suppliers",
                "decision": "ok",
                "n": len(ranked[:6]),
            }
        ],
    }
