"""Уведомления в n8n (escalation, alert).

Невалящий слой: если n8n недоступен или URL не настроен — пишем в лог и
возвращаем False, чтобы пайплайн не падал.
"""
from __future__ import annotations

import logging

import httpx

from ..settings import settings

log = logging.getLogger(__name__)


async def notify_escalation(
    *,
    lot_id: str,
    severity: str,
    reason: str,
    customer_name: str | None = None,
    raw_request_preview: str | None = None,
) -> bool:
    """Шлёт POST в n8n. Возвращает True при успехе, False — при ошибке.

    Не выбрасывает исключений: ошибки сети/n8n не должны валить пайплайн.
    """
    # Метрика инкрементится в любом случае — отражает что эскалация была инициирована
    try:
        from ..api.metrics import ESCALATIONS

        ESCALATIONS.labels(reason=(reason or "unknown")[:40], severity=severity).inc()
    except Exception:
        pass

    url = settings.n8n_webhook_escalation
    if not url:
        log.info("n8n_webhook_escalation not configured — skip notify lot=%s", lot_id)
        return False
    payload = {
        "lot_id": lot_id,
        "severity": severity,
        "reason": reason,
        "customer_name": customer_name,
        "raw_request_preview": (raw_request_preview or "")[:300],
        "lot_url": f"{settings.service_public_url}/lots/{lot_id}",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.post(url, json=payload)
            r.raise_for_status()
        log.info("n8n escalation OK lot=%s severity=%s", lot_id, severity)
        return True
    except httpx.HTTPError as e:
        log.warning("n8n escalation failed lot=%s: %s", lot_id, e)
        return False


async def notify_alert(
    *,
    title: str,
    message: str,
    level: str = "warning",
    metadata: dict | None = None,
) -> bool:
    """Шлёт generic-алёрт (например, метрики, health-чек)."""
    url = settings.n8n_webhook_escalation  # переиспользуем тот же канал
    if not url:
        return False
    payload = {
        "type": "alert",
        "level": level,
        "title": title,
        "message": message,
        "metadata": metadata or {},
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.post(url, json=payload)
            r.raise_for_status()
        return True
    except httpx.HTTPError as e:
        log.warning("n8n alert failed: %s", e)
        return False
