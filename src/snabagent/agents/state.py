"""LangGraph state-объект для лота."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict


class LotState(TypedDict, total=False):
    lot_id: str
    customer_id: str
    raw_request: str
    attachments: list[str]
    phase: str  # pre_nmck | post_tender_published | unregulated
    category: str | None
    total_estimated_rub: float | None

    parsed_items: list[dict]
    nsi_matches: list[dict]
    requires_human: bool
    escalation_reason: str | None

    suppliers: list[dict]
    rfq_emails_sent: list[dict]
    responses_collected: list[dict]
    negotiations: list[dict]
    verifications: list[dict]
    report: dict | None

    # Persistent memory (MemoryAgent): подгружается узлом memory_recall в начале графа.
    #   profile      — предпочтения компании (цена/срок/качество)
    #   supplier_memory — накопленные скоры надёжности поставщиков (по ИНН)
    #   past_lots    — похожие прошлые лоты и решения
    memory: dict

    status: str
    audit_events: Annotated[list[dict], add]
    errors: Annotated[list[str], add]
