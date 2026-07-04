"""Reporter — финальный отчёт: Top-3 + savings."""
from __future__ import annotations

from typing import Any

from ..audit import write_audit
from ..llm.router import complete_with_fallback
from . import prompts
from .state import LotState


async def reporter_node(state: LotState) -> dict[str, Any]:
    lot_id = state["lot_id"]
    verifications = state.get("verifications") or []
    items = state.get("parsed_items") or []

    # Сортируем по (confidence DESC, total_price ASC)
    ranked = sorted(
        verifications,
        key=lambda v: (-(v.get("confidence_score") or 0.0), (v.get("offer") or {}).get("total_price", 1e12)),
    )
    top = ranked[:3]
    top_norm = [
        {
            "supplier_name": t["supplier_name"],
            "inn": t["inn"],
            "total_price_rub": t["offer"]["total_price"],
            "lead_time_days": t["offer"].get("lead_time_days"),
            "score": t["confidence_score"],
            "discrepancies": t["discrepancies"],
            "rationale": (
                "Прошёл верификацию: ИНН в реестре, сроки и ГОСТ соответствуют спецификации."
                if not t["discrepancies"]
                else f"Прошёл с оговорками: {len(t['discrepancies'])} несоответствий"
            ),
            "recommendation": t["recommendation"],
        }
        for t in top
    ]

    # savings vs typical
    typical_total = 0.0
    for i in items:
        typical = (i.get("typical_price_rub") or 0)
        qty = i.get("qty") or 0
        # typical_price может быть из НСИ — если planner его не передал, оставляем 0
        typical_total += float(typical) * float(qty)
    best_total = top[0]["offer"]["total_price"] if top else 0
    savings_rub = max(0.0, typical_total - best_total)
    savings_pct = round((savings_rub / typical_total * 100) if typical_total else 0.0, 2)

    # LLM summary (для презентационности)
    pad_top = top_norm + [
        {"supplier_name": "—", "total_price_rub": 0, "lead_time_days": 0}
    ] * 3
    prompt = prompts.render(
        "reporter_summary.j2",
        lot_summary=f"{len(items)} позиций, категория {state.get('category')}",
        n_responses=len(state.get("responses_collected") or []),
        n_verified=len(verifications),
        top1=pad_top[0],
        top2=pad_top[1],
        top3=pad_top[2],
        savings_pct=savings_pct,
        savings_rub=int(savings_rub),
    )
    resp = await complete_with_fallback("Ты менеджер по снабжению. Кратко и по фактам.", prompt)
    summary = resp.text

    next_action = "send_to_human_for_approval"
    if not top_norm:
        next_action = "escalate"

    report = {
        "summary": summary,
        "top_3": top_norm,
        "savings_vs_avg_rub": int(savings_rub),
        "savings_vs_avg_pct": savings_pct,
        "risk_flags": [
            d for v in top for d in (v.get("discrepancies") or [])
        ],
        "next_action": next_action,
        "human_review_required": True,
    }

    await write_audit(
        lot_id=lot_id,
        agent_name="reporter",
        step_name="build_report",
        input_payload={"n_verifications": len(verifications), "savings_pct": savings_pct},
        output_payload=report,
        prompt_text=prompt[:3000],
        llm_response_raw=resp.raw,
        model_name=resp.model_name,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        latency_ms=resp.latency_ms,
        confidence=0.9,
        decision="ok",
    )

    return {
        "report": report,
        "status": "report_ready",
        "audit_events": [{"agent_name": "reporter", "step_name": "build_report"}],
    }
