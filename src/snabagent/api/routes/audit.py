"""Endpoints для audit-log."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...audit.logger import serialize_audit
from ...db.models import AuditLog
from ...db.repositories import LotRepo
from ...db.session import get_session

router = APIRouter(prefix="/lots", tags=["audit"])


@router.get("/{lot_id}/audit")
async def get_audit_for_lot(lot_id: UUID, session: AsyncSession = Depends(get_session)):
    events = await LotRepo(session).audit_log(lot_id)
    return [serialize_audit(e) for e in events]


@router.get("/audit/global")
async def audit_global(limit: int = 200, agent_name: str | None = None, session: AsyncSession = Depends(get_session)):
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if agent_name:
        q = q.where(AuditLog.agent_name == agent_name)
    rows = (await session.execute(q)).scalars().all()
    return [serialize_audit(e) for e in rows]
