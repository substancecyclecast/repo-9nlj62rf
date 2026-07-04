"""Billing — Mandate's revenue model and per-org invoicing.

Revenue = a take-rate (bps) on *settled* payment volume + a flat monthly SaaS
platform fee. This module computes the current invoice, lifetime/MTD revenue, and
the data the in-app billing page renders.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Payment, PayrollBatch


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def summary(db: Session, organization_id: int) -> dict:
    take_rate_bps = settings.billing_take_rate_bps
    platform_fee = settings.billing_platform_fee_usd

    batches = db.scalars(
        select(PayrollBatch).where(PayrollBatch.organization_id == organization_id)
    ).all()

    settled_volume = 0.0
    payment_count = 0
    fees_saved_vs_swift = 0.0
    by_month: dict[str, float] = defaultdict(float)

    for b in batches:
        if b.status != "executed":
            continue
        settled_volume += b.total_usd
        payment_count += b.payment_count
        if b.created_at:
            by_month[_month_key(b.created_at)] += b.total_usd

    # Cross-border savings story: SWIFT averages ~$35/transfer; we estimate
    # realized savings as the delta between a SWIFT baseline and actual fees.
    payments = db.scalars(
        select(Payment).join(PayrollBatch).where(PayrollBatch.organization_id == organization_id)
    ).all()
    actual_fees = sum(p.fee_usd for p in payments if p.status == "executed")
    swift_baseline = sum(35.0 for p in payments if p.status == "executed")
    fees_saved_vs_swift = max(0.0, swift_baseline - actual_fees)

    take_rate_revenue = settled_volume * take_rate_bps / 10_000.0

    now = datetime.now(timezone.utc)
    mtd_volume = by_month.get(_month_key(now), 0.0)
    mtd_take_rate = mtd_volume * take_rate_bps / 10_000.0
    current_invoice = mtd_take_rate + platform_fee

    return {
        "currency": settings.billing_currency,
        "plan": "Scale",
        "take_rate_bps": take_rate_bps,
        "platform_fee_usd": platform_fee,
        "settled_volume_usd": round(settled_volume, 2),
        "payment_count": payment_count,
        "lifetime_take_rate_revenue_usd": round(take_rate_revenue, 2),
        "mtd_volume_usd": round(mtd_volume, 2),
        "mtd_take_rate_usd": round(mtd_take_rate, 2),
        "estimated_mrr_usd": round(platform_fee + mtd_take_rate, 2),
        "current_invoice_usd": round(current_invoice, 2),
        "fees_saved_vs_swift_usd": round(fees_saved_vs_swift, 2),
        "volume_by_month": {k: round(v, 2) for k, v in sorted(by_month.items())},
    }


def invoice(db: Session, organization_id: int) -> dict:
    s = summary(db, organization_id)
    now = datetime.now(timezone.utc)
    line_items = [
        {
            "description": "Mandate platform fee (Scale plan)",
            "quantity": 1,
            "unit_usd": s["platform_fee_usd"],
            "amount_usd": s["platform_fee_usd"],
        },
        {
            "description": (
                f"Payment processing — {s['take_rate_bps']} bps on "
                f"${s['mtd_volume_usd']:,.0f} settled volume"
            ),
            "quantity": s["payment_count"],
            "unit_usd": None,
            "amount_usd": s["mtd_take_rate_usd"],
        },
    ]
    return {
        "invoice_number": f"MND-{organization_id:03d}-{now.strftime('%Y%m')}",
        "period": now.strftime("%B %Y"),
        "currency": s["currency"],
        "line_items": line_items,
        "subtotal_usd": s["current_invoice_usd"],
        "total_usd": s["current_invoice_usd"],
        "status": "open",
        "issued_at": now.date().isoformat(),
    }
