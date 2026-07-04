"""Verifier — независимая верификация КП через DIFFERENT LLM (role=verifier)."""
from __future__ import annotations

import json
from typing import Any

from ..audit import write_audit
from ..db.repositories import VerificationRepo
from ..db.session import AsyncSessionLocal
from ..llm.router import complete_with_fallback
from . import prompts
from .state import LotState
from .tools.spark_mock import check_inn_ogrn


async def verifier_node(state: LotState) -> dict[str, Any]:
    lot_id = state["lot_id"]
    items = state.get("parsed_items") or []
    responses = state.get("responses_collected") or []

    lot_spec = {
        "items": [
            {
                "sku": i.get("matched_nsi_sku"),
                "name": i.get("matched_nsi_name"),
                "qty": i.get("qty"),
                "unit": i.get("unit"),
                "lead_time_days": i.get("lead_time_days"),
            }
            for i in items
        ],
        "category": state.get("category"),
    }
    requested_lt = max((i.get("lead_time_days") or 30) for i in items) if items else 30

    verifications = []
    for r in responses:
        supplier = r["supplier"]
        offer = r["offer"]
        spark_data = await check_inn_ogrn(supplier.get("inn") or "") or {"active": False}
        prompt = prompts.render(
            "verifier_check.j2",
            lot_spec_json=json.dumps(lot_spec, ensure_ascii=False),
            offer_json=json.dumps(offer, ensure_ascii=False),
            supplier_inn=supplier.get("inn"),
            spark_data_json=json.dumps(spark_data, ensure_ascii=False),
            requested_lead_time=requested_lt,
            offered_lead_time=offer.get("lead_time_days"),
        )
        # ВАЖНО: role='verifier' — модель должна отличаться от primary
        resp = await complete_with_fallback("Ты независимый аудитор закупочной службы. Отвечай JSON.", prompt, role="verifier")
        try:
            check = json.loads(resp.text)
        except json.JSONDecodeError:
            check = {"discrepancies": [], "confidence_score": 0.5, "recommendation": "escalate_to_human"}

        ver_record = {
            "supplier_id": supplier.get("supplier_id"),
            "supplier_name": supplier.get("name"),
            "inn": supplier.get("inn"),
            "inn_valid": bool(spark_data and spark_data.get("active")),
            "ogrn_valid": bool(spark_data and spark_data.get("ogrn")),
            "spark_match": bool(spark_data),
            "discrepancies": check.get("discrepancies") or [],
            "confidence_score": float(check.get("confidence_score") or 0.5),
            "recommendation": check.get("recommendation") or "escalate_to_human",
            "lead_time_meets_spec": (offer.get("lead_time_days") or 999) <= requested_lt,
            "gost_match": True,
            "verifier_model": resp.model_name,
            "offer": offer,
        }
        verifications.append(ver_record)

        async with AsyncSessionLocal() as session:
            await VerificationRepo(session).create(
                lot_id=lot_id,
                supplier_id=supplier.get("supplier_id"),
                inn_valid=ver_record["inn_valid"],
                ogrn_valid=ver_record["ogrn_valid"],
                spark_match=ver_record["spark_match"],
                price_consistent=True,
                lead_time_meets_spec=ver_record["lead_time_meets_spec"],
                gost_match=ver_record["gost_match"],
                discrepancies=ver_record["discrepancies"],
                confidence_score=ver_record["confidence_score"],
                verifier_model=resp.model_name,
            )

        await write_audit(
            lot_id=lot_id,
            agent_name="verifier",
            step_name="check_offer",
            input_payload={"inn": supplier.get("inn"), "total_price": offer.get("total_price")},
            output_payload=check,
            prompt_text=prompt[:3000],
            llm_response_raw=resp.raw,
            model_name=resp.model_name,
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
            latency_ms=resp.latency_ms,
            confidence=ver_record["confidence_score"],
            decision=ver_record["recommendation"],
        )

    return {
        "verifications": verifications,
        "status": "verified",
        "audit_events": [{"agent_name": "verifier", "step_name": "check_offer", "n": len(verifications)}],
    }
