"""Payroll, batch payout, transfer, swap, and yield endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.swap import swap
from app.adapters.yield_venues import yield_adapter
from app.agent.tools import ToolContext, deploy_yield, propose_transfer
from app.api.schemas import (
    DeployYieldRequest,
    PayrollJsonRequest,
    SwapRequest,
    TransferRequest,
)
from app.core.database import get_db
from app.models import Contractor, PayrollBatch, Transaction
from app.services import audit_service, payroll_service, webhooks

router = APIRouter(tags=["payments"])


def _serialize_batch(batch: PayrollBatch) -> dict:
    return {
        "id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "total_usd": batch.total_usd,
        "total_fees_usd": batch.total_fees_usd,
        "payment_count": batch.payment_count,
        "created_at": batch.created_at.isoformat(),
        "payments": [
            {
                "id": p.id,
                "payee_name": p.payee_name,
                "country": p.country,
                "amount_usd": p.amount_usd,
                "chain": p.chain,
                "asset": p.asset,
                "to_address": p.to_address,
                "fee_usd": p.fee_usd,
                "route": p.route,
                "status": p.status,
                "memo": p.memo,
            }
            for p in batch.payments
        ],
    }


@router.get("/orgs/{org_id}/contractors")
def contractors(org_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(Contractor).where(Contractor.organization_id == org_id).order_by(Contractor.name)
    ).all()
    return [
        {
            "id": c.id, "name": c.name, "email": c.email, "country": c.country,
            "role": c.role, "payout_chain": c.payout_chain, "payout_asset": c.payout_asset,
            "wallet_address": c.wallet_address, "kyc_status": c.kyc_status,
            "prefers_fiat": c.prefers_fiat,
        }
        for c in rows
    ]


@router.post("/orgs/{org_id}/payroll/upload")
async def upload_payroll(
    org_id: int,
    name: str = "Payroll batch",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    content = (await file.read()).decode("utf-8")
    try:
        rows = payroll_service.parse_csv(content)
        batch = payroll_service.build_plan(db, organization_id=org_id, name=name, rows=rows)
    except payroll_service.PayrollError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(batch)
    return _serialize_batch(batch)


@router.post("/orgs/{org_id}/payroll/sample")
def create_sample_payroll(
    org_id: int, name: str = "Sample payroll (12 contractors)", db: Session = Depends(get_db)
) -> dict:
    """One-click demo: build a batch from the bundled sample contractor CSV."""
    import pathlib

    sample = pathlib.Path(__file__).resolve().parents[2] / "data" / "sample_payroll.csv"
    try:
        rows = payroll_service.parse_csv(sample.read_text())
        batch = payroll_service.build_plan(db, organization_id=org_id, name=name, rows=rows)
    except (payroll_service.PayrollError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(batch)
    return _serialize_batch(batch)


@router.post("/orgs/{org_id}/payroll/json")
def create_payroll_json(
    org_id: int, body: PayrollJsonRequest, db: Session = Depends(get_db)
) -> dict:
    rows = [r.model_dump() for r in body.rows]
    try:
        batch = payroll_service.build_plan(db, organization_id=org_id, name=body.name, rows=rows)
        proposal = payroll_service.propose_batch(db, batch_id=batch.id)
        if body.auto_execute:
            payroll_service.execute_batch(db, batch_id=batch.id)
    except payroll_service.PayrollError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(batch)
    return {"batch": _serialize_batch(batch), "proposals": proposal["proposals"]}


@router.get("/orgs/{org_id}/payroll/batches")
def list_batches(org_id: int, db: Session = Depends(get_db)) -> list[dict]:
    batches = db.scalars(
        select(PayrollBatch)
        .where(PayrollBatch.organization_id == org_id)
        .order_by(PayrollBatch.created_at.desc())
    ).all()
    return [_serialize_batch(b) for b in batches]


@router.get("/orgs/{org_id}/payroll/batches/{batch_id}")
def get_batch(org_id: int, batch_id: int, db: Session = Depends(get_db)) -> dict:
    batch = db.get(PayrollBatch, batch_id)
    if batch is None or batch.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _serialize_batch(batch)


@router.post("/orgs/{org_id}/payroll/batches/{batch_id}/propose")
def propose_batch(org_id: int, batch_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        result = payroll_service.propose_batch(db, batch_id=batch_id)
    except payroll_service.PayrollError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/orgs/{org_id}/payroll/batches/{batch_id}/execute")
def execute_batch(org_id: int, batch_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        result = payroll_service.execute_batch(db, batch_id=batch_id)
    except payroll_service.PayrollError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_service.record(
        db,
        organization_id=org_id,
        action="payroll.executed",
        resource=f"batch:{batch_id}",
        detail=result,
    )
    webhooks.emit(
        db,
        event="payroll.executed",
        summary=f"Settled {result.get('executed_payments', 0)} payments",
        organization_id=org_id,
        fields={
            "total_usd": result.get("total_usd"),
            "total_fees_usd": result.get("total_fees_usd"),
            "batch_id": batch_id,
        },
    )
    db.commit()
    return result


@router.post("/orgs/{org_id}/transfers")
def create_transfer(org_id: int, body: TransferRequest, db: Session = Depends(get_db)) -> dict:
    ctx = ToolContext(db=db, organization_id=org_id)
    result = propose_transfer(ctx, **body.model_dump())
    db.commit()
    return {"ok": result.ok, "message": result.message, "data": result.data}


@router.get("/orgs/{org_id}/transactions")
def list_transactions(org_id: int, limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    txs = db.scalars(
        select(Transaction)
        .where(Transaction.organization_id == org_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": t.id, "tx_type": t.tx_type, "status": t.status, "chain": t.chain,
            "asset": t.asset, "amount": t.amount, "usd_value": t.usd_value, "fee_usd": t.fee_usd,
            "counterparty": t.counterparty, "to_address": t.to_address, "category": t.category,
            "memo": t.memo, "tx_hash": t.tx_hash, "safe_tx_hash": t.safe_tx_hash,
            "created_at": t.created_at.isoformat(),
        }
        for t in txs
    ]


@router.post("/orgs/{org_id}/swap/quote")
def swap_quote(org_id: int, body: SwapRequest, db: Session = Depends(get_db)) -> dict:
    q = swap.quote(**body.model_dump())
    return {"ok": q.ok, "detail": q.detail, "data": q.data}


@router.get("/orgs/{org_id}/yield/venues")
def yield_venues(org_id: int, asset: str = "USDC") -> list[dict]:
    return yield_adapter.list_venues(asset)


@router.post("/orgs/{org_id}/yield/deploy")
def yield_deploy(org_id: int, body: DeployYieldRequest, db: Session = Depends(get_db)) -> dict:
    ctx = ToolContext(db=db, organization_id=org_id)
    result = deploy_yield(ctx, **body.model_dump())
    db.commit()
    return {"ok": result.ok, "message": result.message, "data": result.data}
