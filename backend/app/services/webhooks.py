"""Outbound event notifications (Slack / Telegram / generic webhook).

Every emitted event is persisted to the ``webhook_deliveries`` outbox so there is
a durable record even in sandbox. When a channel is configured (Slack/Telegram
env vars) the message is actually sent; otherwise the delivery is marked
``skipped`` — keeping the demo fully offline while exercising the same code path.
"""

from __future__ import annotations

import json

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import metrics
from app.models import WebhookDelivery


def _format_slack(event: str, summary: str, fields: dict) -> dict:
    lines = [f"*{event}* — {summary}"]
    for k, v in fields.items():
        lines.append(f"• *{k}*: {v}")
    return {"text": "\n".join(lines)}


def emit(
    db: Session,
    *,
    event: str,
    summary: str,
    organization_id: int | None = None,
    fields: dict | None = None,
    commit: bool = False,
) -> list[WebhookDelivery]:
    """Record + (best-effort) send a notification for ``event``."""
    fields = fields or {}
    metrics.inc("mandate_events_emitted_total", event=event)
    deliveries: list[WebhookDelivery] = []

    # Slack
    delivery = WebhookDelivery(
        organization_id=organization_id,
        event=event,
        channel="slack",
        target=settings.slack_webhook_url,
        payload_json=json.dumps(_format_slack(event, summary, fields)),
    )
    if settings.slack_webhook_url:
        try:
            resp = httpx.post(
                settings.slack_webhook_url,
                json=_format_slack(event, summary, fields),
                timeout=5.0,
            )
            delivery.status = "sent" if resp.status_code < 400 else "failed"
            delivery.response_code = resp.status_code
        except Exception as exc:  # pragma: no cover - network failure path
            delivery.status = "failed"
            delivery.error = str(exc)[:500]
    else:
        delivery.status = "skipped"
    db.add(delivery)
    deliveries.append(delivery)

    # Telegram
    if settings.telegram_bot_token and settings.telegram_chat_id:
        text = f"{event}: {summary}\n" + "\n".join(f"{k}: {v}" for k, v in fields.items())
        tg = WebhookDelivery(
            organization_id=organization_id,
            event=event,
            channel="telegram",
            target=f"chat:{settings.telegram_chat_id}",
            payload_json=json.dumps({"text": text}),
        )
        try:
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            resp = httpx.post(url, json={"chat_id": settings.telegram_chat_id, "text": text}, timeout=5.0)
            tg.status = "sent" if resp.status_code < 400 else "failed"
            tg.response_code = resp.status_code
        except Exception as exc:  # pragma: no cover - network failure path
            tg.status = "failed"
            tg.error = str(exc)[:500]
        db.add(tg)
        deliveries.append(tg)

    if commit:
        db.commit()
    return deliveries


def serialize(d: WebhookDelivery) -> dict:
    return {
        "id": d.id,
        "event": d.event,
        "channel": d.channel,
        "target": d.target,
        "status": d.status,
        "response_code": d.response_code,
        "error": d.error,
        "payload": json.loads(d.payload_json or "{}"),
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def list_for_org(db: Session, organization_id: int, limit: int = 50) -> list[dict]:
    rows = db.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.organization_id == organization_id)
        .order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc())
        .limit(limit)
    ).all()
    return [serialize(r) for r in rows]
