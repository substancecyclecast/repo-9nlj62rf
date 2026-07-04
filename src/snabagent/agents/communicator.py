"""Communicator — отправляет RFQ и парсит ответы поставщиков."""
from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from ..audit import write_audit
from ..db.repositories import RfqEmailRepo
from ..db.session import AsyncSessionLocal
from ..email_service.sender import send_rfq_email
from ..settings import settings
from ..utils.id import short_lot_id
from . import prompts
from .state import LotState

CATEGORY_HUMAN = {
    "metals": "металлопрокат",
    "it": "ИТ-оборудование",
    "mro": "MRO/спец-инвентарь",
    "consumables": "канцелярия и расходники",
    "chemistry": "полимеры и химия",
    "services": "услуги",
}


def _make_subject(lot_id: str, category: str) -> str:
    return f"[SnabAgent #LOT-{short_lot_id(lot_id)}] Запрос КП: {CATEGORY_HUMAN.get(category, category)}"


def _synthetic_offer(supplier: dict, items: list[dict]) -> dict:
    """Детерминированный fake-ответ поставщика для DEMO_MODE."""
    inn_str = str(supplier.get("inn") or "0")
    seed_str = inn_str[-5:] if len(inn_str) >= 1 else "1"
    try:
        seed = int(seed_str) or 1
    except ValueError:
        seed = 1
    rng = random.Random(seed)
    discount = rng.uniform(0.85, 1.10)
    total = 0
    lines = []
    for it in items:
        base = float(it.get("typical_price_rub") or 1000)
        qty = float(it.get("qty") or 1)
        unit_price = round(base * discount, 2)
        subtotal = round(unit_price * qty, 2)
        total += subtotal
        lines.append(
            {
                "name": it.get("matched_nsi_name") or it.get("raw_phrase"),
                "matched_sku": it.get("matched_nsi_sku"),
                "qty": qty,
                "unit": it.get("unit"),
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
    lead_time = rng.choice([20, 25, 30, 35, 45])
    return {
        "currency": "RUB",
        "vat_included": True,
        "total_price": round(total, 2),
        "lead_time_days": lead_time,
        "delivery_terms": "FCA склад поставщика",
        "payment_terms": "30 банковских дней по факту",
        "validity_days": 14,
        "items": lines,
        "discrepancies_with_spec": [],
    }


async def communicator_node(state: LotState) -> dict[str, Any]:
    lot_id = state["lot_id"]
    suppliers = state.get("suppliers") or []
    items = state.get("parsed_items") or []
    category = state.get("category") or "mro"

    # ---- 1. Отправить RFQ ------------------------------------------
    reply_to = f"lot+{lot_id}@{settings.demo_email_domain}"
    rfq_body = prompts.render(
        "communicator_rfq.j2",
        lot_short_id=short_lot_id(lot_id),
        category_human=CATEGORY_HUMAN.get(category, category),
        customer_name="SIBUR Demo",
        items=items,
        rfq_deadline=(datetime.now(UTC) + timedelta(days=2)).strftime("%d.%m.%Y 18:00"),
        reply_to_email=reply_to,
    )
    subject = _make_subject(lot_id, category)
    sent_records = []
    for s in suppliers:
        try:
            msg_id = await send_rfq_email(
                supplier_email=s.get("contact_email"),
                subject=subject,
                body=rfq_body,
                reply_to=reply_to,
            )
            sent_records.append({"supplier": s, "message_id": msg_id})
            async with AsyncSessionLocal() as session:
                await RfqEmailRepo(session).create(
                    lot_id=lot_id,
                    supplier_id=s.get("supplier_id"),
                    direction="out",
                    subject=subject,
                    body_text=rfq_body,
                    message_id=msg_id,
                    sent_at=datetime.now(UTC),
                )
        except Exception as e:  # pragma: no cover
            sent_records.append({"supplier": s, "error": str(e)})

    await write_audit(
        lot_id=lot_id,
        agent_name="communicator",
        step_name="send_rfq",
        input_payload={"suppliers_n": len(suppliers)},
        output_payload={"sent": [r.get("supplier", {}).get("inn") for r in sent_records]},
        prompt_text=rfq_body[:3000],
        decision="ok",
        confidence=1.0,
    )

    # ---- 2. Ждать ответы (DEMO_MODE — синтезируем) -----------------
    if settings.demo_mode:
        await asyncio.sleep(0.05)
        responses = []
        n_responding = max(1, int(len(suppliers) * 0.66))
        for s in suppliers[:n_responding]:
            offer = _synthetic_offer(s, items)
            responses.append({"supplier": s, "offer": offer})
            async with AsyncSessionLocal() as session:
                await RfqEmailRepo(session).create(
                    lot_id=lot_id,
                    supplier_id=s.get("supplier_id"),
                    direction="in",
                    subject=f"Re: {subject}",
                    body_text=(
                        f"Коммерческое предложение от {s.get('name')}\n"
                        f"Итого: {offer['total_price']} RUB\n"
                        f"Срок: {offer['lead_time_days']} дн."
                    ),
                    parsed_offer=offer,
                    received_at=datetime.now(UTC),
                    in_reply_to=next(
                        (r["message_id"] for r in sent_records if r.get("supplier", {}).get("inn") == s.get("inn")),
                        None,
                    ),
                )
        await write_audit(
            lot_id=lot_id,
            agent_name="communicator",
            step_name="collect_responses",
            input_payload={"expected": len(suppliers)},
            output_payload={
                "received": len(responses),
                "summary": [{"inn": r["supplier"].get("inn"), "total": r["offer"]["total_price"]} for r in responses],
            },
            decision="ok",
            confidence=0.9,
        )
        return {
            "rfq_emails_sent": [{"inn": r["supplier"].get("inn")} for r in sent_records],
            "responses_collected": responses,
            "status": "responses_collected",
            "audit_events": [
                {"agent_name": "communicator", "step_name": "collect_responses", "n": len(responses)}
            ],
        }
    # Прод-режим: возвращаем без ответов, IMAP-поллер дополнит state позже
    return {
        "rfq_emails_sent": [{"inn": r["supplier"].get("inn")} for r in sent_records],
        "responses_collected": [],
        "status": "rfq_sent",
        "audit_events": [{"agent_name": "communicator", "step_name": "send_rfq"}],
    }
