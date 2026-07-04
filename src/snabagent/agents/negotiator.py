"""Negotiator — один раунд переговоров с LLM-обоснованием. С регуляторным фильтром 223-ФЗ."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from ..audit import write_audit
from ..db.repositories import NegotiationRepo
from ..db.session import AsyncSessionLocal
from ..llm.router import complete_with_fallback
from . import prompts
from .state import LotState
from .tools.regulatory_filter import check as reg_check

log = logging.getLogger(__name__)


async def negotiator_node(state: LotState) -> dict[str, Any]:
    lot_id = state["lot_id"]
    responses = state.get("responses_collected") or []
    if not responses:
        return {"negotiations": [], "status": "negotiating"}

    # Регуляторная проверка
    allow = reg_check(state)
    if not allow.allowed:
        await write_audit(
            lot_id=lot_id,
            agent_name="negotiator",
            step_name="regulatory_block",
            input_payload={"phase": state.get("phase"), "category": state.get("category")},
            output_payload={"reason": allow.reason},
            decision="skip",
            confidence=1.0,
        )
        return {"negotiations": [], "status": "responses_collected"}

    min_total = min(r["offer"]["total_price"] for r in responses)
    avg_total = sum(r["offer"]["total_price"] for r in responses) / len(responses)

    negotiations: list[dict[str, Any]] = []
    for r in responses:
        offer = r["offer"]
        supplier = r["supplier"]
        # Если уже близко к минимуму — не торгуемся (логируем в audit)
        if offer["total_price"] <= min_total * 1.05:
            await write_audit(
                lot_id=lot_id,
                agent_name="negotiator",
                step_name="skip_competitive",
                input_payload={"supplier_inn": supplier.get("inn")},
                output_payload={
                    "offer_total": offer["total_price"],
                    "min_total": min_total,
                    "reason": "already_within_5pct_of_min",
                },
                decision="skip",
                confidence=1.0,
            )
            continue

        # === LLM-вызов: запрашиваем рекомендацию по скидке ===
        sys_prompt = prompts.render("negotiator_system.j2")
        user_prompt = prompts.render(
            "negotiator_user.j2",
            lot_short_id=str(lot_id)[:8],
            category=state.get("category") or "—",
            supplier_name=supplier.get("name") or "?",
            supplier_inn=supplier.get("inn") or "?",
            is_historical=bool(supplier.get("source") == "historical"),
            historical_avg_rub=supplier.get("historical_avg") or avg_total,
            offer_total_price=offer["total_price"],
            offer_qty=offer.get("qty") or 1,
            offer_unit=offer.get("unit") or "",
            min_total_rub=min_total,
            avg_competitor_price=avg_total,
        )
        t0 = time.perf_counter()
        resp = None
        try:
            resp = await complete_with_fallback(sys_prompt, user_prompt, role="primary")
            llm_latency = int((time.perf_counter() - t0) * 1000)
            data = json.loads(resp.text)
            target_discount = float(data.get("suggested_target_discount_pct") or 0)
            rationale = str(data.get("rationale") or "")
            tone_ok = bool(data.get("tone_ok", True))
        except Exception as e:  # noqa: BLE001
            log.warning("negotiator LLM failed: %s; falling back to mechanical 5%%", e)
            target_discount = 5.0
            rationale = "LLM недоступен, применена дефолтная скидка 5%"
            tone_ok = True
            llm_latency = 0
            resp = None

        # Защита от перегиба: ограничиваем сверху 12%
        target_discount = min(12.0, max(0.0, target_discount))
        if target_discount == 0.0:
            await write_audit(
                lot_id=lot_id,
                agent_name="negotiator",
                step_name="llm_no_discount",
                input_payload={"supplier_inn": supplier.get("inn")},
                output_payload={"rationale": rationale, "target_discount_pct": 0},
                prompt_text=user_prompt[:3000],
                llm_response_raw=(resp.raw if resp else {}),
                model_name=(resp.model_name if resp else "fallback-mechanical"),
                prompt_tokens=(resp.prompt_tokens if resp else 0),
                completion_tokens=(resp.completion_tokens if resp else 0),
                latency_ms=llm_latency,
                confidence=0.85 if tone_ok else 0.5,
                decision="ok",
            )
            continue

        new_total = round(offer["total_price"] * (1 - target_discount / 100), 2)
        delta = round((offer["total_price"] - new_total) / offer["total_price"] * 100, 2)
        new_offer = dict(offer)
        new_offer["total_price"] = new_total

        # Сохраняем раунд в БД
        async with AsyncSessionLocal() as session:
            await NegotiationRepo(session).create(
                lot_id=lot_id,
                supplier_id=supplier.get("supplier_id"),
                round_no=1,
                initial_offer=offer,
                target_discount_pct=target_discount,
                final_offer=new_offer,
                delta_pct=delta,
                allowed_by_filter=True,
            )

        # Аудит-лог именно с LLM-промптом и raw-ответом (для трейс-tree)
        await write_audit(
            lot_id=lot_id,
            agent_name="negotiator",
            step_name="llm_round_1",
            input_payload={
                "supplier_inn": supplier.get("inn"),
                "initial_total": offer["total_price"],
                "min_total": min_total,
            },
            output_payload={
                "rationale": rationale,
                "target_discount_pct": target_discount,
                "new_total": new_total,
                "delta_pct": delta,
                "tone_ok": tone_ok,
            },
            prompt_text=user_prompt[:3000],
            llm_response_raw=(resp.raw if resp else {}),
            model_name=(resp.model_name if resp else "fallback-mechanical"),
            prompt_tokens=(resp.prompt_tokens if resp else 0),
            completion_tokens=(resp.completion_tokens if resp else 0),
            latency_ms=llm_latency,
            confidence=0.85 if tone_ok else 0.5,
            decision="ok",
        )

        negotiations.append({
            "supplier": supplier,
            "before": offer,
            "after": new_offer,
            "delta_pct": delta,
            "rationale": rationale,
        })
        r["offer"] = new_offer

    avg_delta = (
        sum(n["delta_pct"] for n in negotiations) / max(1, len(negotiations))
        if negotiations else 0.0
    )
    await write_audit(
        lot_id=lot_id,
        agent_name="negotiator",
        step_name="round_summary",
        input_payload={"n_responses": len(responses)},
        output_payload={
            "n_negotiated": len(negotiations),
            "avg_delta_pct": avg_delta,
            "total_savings_rub": sum(
                n["before"]["total_price"] - n["after"]["total_price"] for n in negotiations
            ),
        },
        decision="ok",
        confidence=0.9,
    )

    return {
        "negotiations": negotiations,
        "responses_collected": responses,
        "status": "negotiating",
        "audit_events": [{"agent_name": "negotiator", "step_name": "llm_round_1"}],
    }
