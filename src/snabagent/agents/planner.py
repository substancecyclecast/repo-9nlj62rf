"""Planner — парсит сырой запрос, маппит на НСИ через вектор-поиск + LLM-валидацию."""
from __future__ import annotations

import json
import re
from typing import Any

from ..audit import write_audit
from ..integrations.n8n import notify_escalation
from ..llm.router import complete_with_fallback
from . import prompts
from .state import LotState
from .tools.nsi_search import nsi_search


def _split_phrases(raw: str) -> list[str]:
    """Эвристика: разбиваем по списочным маркерам, нумерации, переносам."""
    lines = re.split(r"[\n;]+", raw)
    phrases = []
    for ln in lines:
        ln = re.sub(r"^[\s\-•*]*\d*[).\s]*", "", ln).strip()
        if not ln:
            continue
        # отрезаем явные хвосты «контакт / срок / заявка №…»
        if re.match(r"^(заявк|цех|вопрос|контакт|если что|срок|спасибо|с уваж|тел)", ln, flags=re.IGNORECASE):
            continue
        if 4 <= len(ln) <= 250:
            phrases.append(ln)
    return phrases[:30]


async def planner_node(state: LotState) -> dict[str, Any]:
    raw = state.get("raw_request", "")
    lot_id = state["lot_id"]
    customer_id = state.get("customer_id") or ""

    phrases = _split_phrases(raw)
    phrase_to_cands: dict[str, list[dict]] = {}
    for phrase in phrases:
        cands = await nsi_search(phrase, customer_id=customer_id, top_k=5)
        if cands:
            phrase_to_cands[phrase] = cands

    if not phrase_to_cands:
        await write_audit(
            lot_id=lot_id,
            agent_name="planner",
            step_name="no_candidates",
            input_payload={"raw_request": raw[:600], "phrases": phrases},
            output_payload={"reason": "no nsi candidates"},
            decision="escalate",
        )
        # Сразу бьем эскалацию в n8n → Telegram/Slack
        await notify_escalation(
            lot_id=str(lot_id),
            severity="high",
            reason="planner_no_candidates",
            raw_request_preview=raw,
        )
        return {
            "parsed_items": [],
            "category": None,
            "requires_human": True,
            "escalation_reason": "Не удалось извлечь позиции из запроса",
            "status": "escalated",
            "audit_events": [
                {
                    "agent_name": "planner",
                    "step_name": "no_candidates",
                    "decision": "escalate",
                }
            ],
        }

    system = prompts.render("planner_system.j2")
    user = prompts.render(
        "planner_user.j2",
        raw_request=raw,
        customer_name="SIBUR Demo",
        phase=state.get("phase", "pre_nmck"),
        phrases=phrase_to_cands,
    )
    resp = await complete_with_fallback(system, user, json_schema={"type": "object"})
    try:
        parsed = json.loads(resp.text)
    except json.JSONDecodeError:
        parsed = {"items": [], "category": None, "overall_confidence": 0.0, "escalation_needed": True}

    items = parsed.get("items") or []
    overall = float(parsed.get("overall_confidence") or 0.0)
    requires_human = bool(parsed.get("escalation_needed", overall < 0.65))
    escalation_reason = parsed.get("escalation_reason") if requires_human else None

    # P0-5: авто-расчёт total_estimated_rub → регуляторный фильтр по сумме
    total_estimated_rub = 0.0
    for it in items:
        typical = it.get("typical_price_rub")
        qty = it.get("qty") or 1
        if typical is not None:
            try:
                total_estimated_rub += float(typical) * float(qty)
            except (TypeError, ValueError):
                pass

    await write_audit(
        lot_id=lot_id,
        agent_name="planner",
        step_name="map_to_nsi",
        input_payload={"raw_request": raw[:600], "phrases": list(phrase_to_cands)},
        output_payload={**parsed, "total_estimated_rub": round(total_estimated_rub, 2)},
        prompt_text=user,
        llm_response_raw=resp.raw,
        model_name=resp.model_name,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        latency_ms=resp.latency_ms,
        confidence=overall,
        decision="escalate" if requires_human else "ok",
    )

    # P0-2: вызываем n8n-эскалацию при низкой уверенности / явном флаге
    if requires_human:
        await notify_escalation(
            lot_id=str(lot_id),
            severity="medium" if overall >= 0.45 else "high",
            reason=escalation_reason or "low_planner_confidence",
            raw_request_preview=raw,
        )

    return {
        "parsed_items": items,
        "category": parsed.get("category"),
        "total_estimated_rub": round(total_estimated_rub, 2),
        "requires_human": requires_human,
        "escalation_reason": escalation_reason,
        "status": "planned",
        "audit_events": [
            {
                "agent_name": "planner",
                "step_name": "map_to_nsi",
                "decision": "escalate" if requires_human else "ok",
                "confidence": overall,
            }
        ],
    }
