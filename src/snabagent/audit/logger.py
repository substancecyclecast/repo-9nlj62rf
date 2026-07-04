"""Запись событий аудит-лога с PII-маскингом.

Все строки во входящих payload-ах и prompt-ах прогоняются через mask_pii,
чтобы в БД не попадали ИНН/ОГРН/email/телефон в открытом виде.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from ..db.models import AuditLog
from ..db.session import AsyncSessionLocal
from ..llm.pii_masker import mask_pii

log = logging.getLogger(__name__)


def _mask_value(v: Any) -> Any:
    """Рекурсивно маскирует строки в dict/list/scalar."""
    if isinstance(v, str):
        masked, _ = mask_pii(v)
        return masked
    if isinstance(v, dict):
        return {k: _mask_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_mask_value(x) for x in v]
    if isinstance(v, tuple):
        return tuple(_mask_value(x) for x in v)
    return v


async def write_audit(
    *,
    lot_id: UUID | str,
    agent_name: str,
    step_name: str,
    input_payload: dict | None = None,
    output_payload: dict | None = None,
    prompt_text: str | None = None,
    llm_response_raw: dict | None = None,
    model_name: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    latency_ms: int | None = None,
    confidence: float | None = None,
    decision: str | None = None,
    error: str | None = None,
) -> None:
    # === PII-маскинг перед записью ===
    if prompt_text:
        prompt_text, _ = mask_pii(prompt_text)
        prompt_text = prompt_text[:8000]  # лимит на размер
    if llm_response_raw:
        llm_response_raw = _mask_value(llm_response_raw)
    if input_payload:
        input_payload = _mask_value(input_payload)
    if output_payload:
        output_payload = _mask_value(output_payload)
    # =================================

    async with AsyncSessionLocal() as s:
        event = AuditLog(
            lot_id=str(lot_id),
            agent_name=agent_name,
            step_name=step_name,
            input_payload=input_payload or {},
            output_payload=output_payload or {},
            prompt_text=prompt_text,
            llm_response_raw=llm_response_raw or {},
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            confidence=confidence,
            decision=decision,
            error=error,
        )
        s.add(event)
        await s.commit()
    # WebSocket notify (соединение опционально)
    try:
        from ..api.ws import bus

        await bus.publish(
            str(lot_id),
            {
                "type": "audit",
                "agent_name": agent_name,
                "step_name": step_name,
                "decision": decision,
                "confidence": confidence,
                "latency_ms": latency_ms,
                "model_name": model_name,
            },
        )
    except Exception as e:  # pragma: no cover
        log.debug("WS publish failed: %s", e)


def serialize_audit(event: Any) -> dict:
    """AuditLog ORM -> dict для API/UI."""
    return {
        "id": str(event.id),
        "lot_id": str(event.lot_id),
        "agent_name": event.agent_name,
        "step_name": event.step_name,
        "input_payload": event.input_payload,
        "output_payload": event.output_payload,
        "prompt_text": event.prompt_text,
        "llm_response_raw": event.llm_response_raw,
        "model_name": event.model_name,
        "prompt_tokens": event.prompt_tokens,
        "completion_tokens": event.completion_tokens,
        "latency_ms": event.latency_ms,
        "confidence": float(event.confidence) if event.confidence is not None else None,
        "decision": event.decision,
        "error": event.error,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
