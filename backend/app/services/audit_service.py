"""Audit log helpers — write immutable records and query them back."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    *,
    action: str,
    organization_id: int | None = None,
    actor: str = "system",
    resource: str = "",
    method: str = "",
    path: str = "",
    status_code: int = 0,
    ip_address: str = "",
    request_id: str = "",
    detail: dict | None = None,
    commit: bool = False,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        actor=actor,
        action=action,
        resource=resource,
        method=method,
        path=path,
        status_code=status_code,
        ip_address=ip_address,
        request_id=request_id,
        detail_json=json.dumps(detail or {}, default=str),
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry


def serialize(entry: AuditLog) -> dict:
    return {
        "id": entry.id,
        "organization_id": entry.organization_id,
        "actor": entry.actor,
        "action": entry.action,
        "resource": entry.resource,
        "method": entry.method,
        "path": entry.path,
        "status_code": entry.status_code,
        "ip_address": entry.ip_address,
        "request_id": entry.request_id,
        "detail": json.loads(entry.detail_json or "{}"),
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def list_for_org(db: Session, organization_id: int, limit: int = 100) -> list[dict]:
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return [serialize(r) for r in rows]
