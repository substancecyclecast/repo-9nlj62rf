"""Export routes: PDF reports, CSV/JSON for BI integration."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.repositories import LotRepo
from ...db.session import get_session
from ...services.export import generate_lot_report_html, lots_to_csv, lots_to_jsonl
from ..auth import Principal, get_principal

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/lots/{lot_id}/report.html")
async def lot_report_html(
    lot_id: UUID,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    """Generate HTML report for a lot (can be converted to PDF)."""
    lot = await LotRepo(session).get(lot_id)
    if not lot:
        raise HTTPException(404, "Lot not found")
    report = lot.final_report or {}
    html = generate_lot_report_html(lot, report)
    return HTMLResponse(content=html)


@router.get("/lots.csv")
async def export_lots_csv(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    """Export lots as CSV for BI tools (PowerBI, Tableau, DataLens)."""
    if not (principal.is_admin or principal.is_system):
        raise HTTPException(403, "Only admin/analyst can export data")

    lots = await LotRepo(session).list(limit=10000, customer_id=principal.filter_customer_id())
    data = [
        {
            "id": str(lot.id),
            "status": lot.status.value,
            "category": lot.category or "",
            "phase": lot.phase.value if lot.phase else "",
            "customer_id": str(lot.customer_id),
            "total_estimated_rub": float(lot.total_estimated_rub) if lot.total_estimated_rub else "",
            "created_at": lot.created_at.isoformat() if lot.created_at else "",
            "updated_at": lot.updated_at.isoformat() if lot.updated_at else "",
            "closed_at": lot.closed_at.isoformat() if lot.closed_at else "",
            "requires_human": lot.requires_human or False,
            "escalation_reason": lot.escalation_reason or "",
        }
        for lot in lots
    ]
    csv_content = lots_to_csv(data)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lots_export.csv"},
    )


@router.get("/lots.json")
async def export_lots_json(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    """Export lots as JSON Lines for BI tools."""
    if not (principal.is_admin or principal.is_system):
        raise HTTPException(403, "Only admin/analyst can export data")

    lots = await LotRepo(session).list(limit=10000, customer_id=principal.filter_customer_id())
    data = [
        {
            "id": str(lot.id),
            "status": lot.status.value,
            "category": lot.category or "",
            "phase": lot.phase.value if lot.phase else "",
            "customer_id": str(lot.customer_id),
            "total_estimated_rub": float(lot.total_estimated_rub) if lot.total_estimated_rub else None,
            "created_at": lot.created_at.isoformat() if lot.created_at else None,
            "updated_at": lot.updated_at.isoformat() if lot.updated_at else None,
            "closed_at": lot.closed_at.isoformat() if lot.closed_at else None,
            "requires_human": lot.requires_human or False,
            "escalation_reason": lot.escalation_reason or "",
        }
        for lot in lots
    ]
    jsonl_content = lots_to_jsonl(data)
    return PlainTextResponse(
        content=jsonl_content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=lots_export.jsonl"},
    )
