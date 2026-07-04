"""LLM-парсер коммерческих предложений (KP)."""
from __future__ import annotations

import json

from ...llm.router import complete_with_fallback
from ...parsers import extract_text_from_path

OFFER_SCHEMA = {
    "type": "object",
    "required": ["currency", "items"],
    "properties": {
        "currency": {"type": "string"},
        "vat_included": {"type": "boolean"},
        "total_price": {"type": "number"},
        "lead_time_days": {"type": "integer"},
        "items": {"type": "array"},
    },
}


async def parse_offer_from_text(text: str, lot_spec: dict) -> dict:
    sys = (
        "Ты парсер коммерческих предложений (КП) от российских поставщиков. "
        "Извлеки структурированные данные. Отвечай ТОЛЬКО валидным JSON."
    )
    user = (
        "Спецификация лота:\n" + json.dumps(lot_spec, ensure_ascii=False) +
        "\n\nТекст КП:\n" + text +
        "\n\nВерни JSON по схеме Offer."
    )
    resp = await complete_with_fallback(sys, user, json_schema=OFFER_SCHEMA)
    try:
        return json.loads(resp.text)
    except json.JSONDecodeError:
        return {
            "currency": "RUB",
            "vat_included": True,
            "total_price": 0,
            "lead_time_days": 30,
            "items": [],
            "discrepancies_with_spec": ["raw_kp_unparseable"],
        }


async def parse_offer_from_path(path: str, lot_spec: dict) -> dict:
    text = extract_text_from_path(path)
    return await parse_offer_from_text(text, lot_spec)
