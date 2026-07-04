"""Operational models: immutable audit log and webhook delivery outbox.

These back the SOC2-style audit trail and the Slack/Telegram event notifications
that a buyer/acquirer expects from a production fintech SaaS.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Append-only record of every significant action (API mutation or event)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), index=True, nullable=True
    )
    actor: Mapped[str] = mapped_column(String(128), default="system")  # user id / "agent" / "system"
    action: Mapped[str] = mapped_column(String(64), index=True)  # e.g. payroll.executed
    resource: Mapped[str] = mapped_column(String(64), default="")  # e.g. batch:12
    method: Mapped[str] = mapped_column(String(8), default="")
    path: Mapped[str] = mapped_column(String(256), default="")
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    request_id: Mapped[str] = mapped_column(String(64), default="")
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class WebhookDelivery(Base):
    """Outbox row for an outbound notification (Slack/Telegram/generic)."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), index=True, nullable=True
    )
    event: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="slack")  # slack | telegram | generic
    target: Mapped[str] = mapped_column(String(256), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|sent|skipped|failed
    response_code: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
