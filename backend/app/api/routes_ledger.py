"""Accounting & reporting endpoints (ledger, trial balance, exports, PDF)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import JournalEntry
from app.reports import auditor_pdf, quickbooks_csv
from app.services import ledger_service

router = APIRouter(tags=["accounting"])


@router.get("/orgs/{org_id}/ledger/trial-balance")
def trial_balance(org_id: int, db: Session = Depends(get_db)) -> dict:
    rows = ledger_service.trial_balance(db, org_id)
    total_debit = round(sum(r["debit"] for r in rows), 2)
    total_credit = round(sum(r["credit"] for r in rows), 2)
    return {
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balanced": abs(total_debit - total_credit) < 0.005,
    }


@router.get("/orgs/{org_id}/ledger/income-statement")
def income_statement(org_id: int, db: Session = Depends(get_db)) -> dict:
    return ledger_service.income_statement(db, org_id)


@router.get("/orgs/{org_id}/ledger/journal")
def journal(org_id: int, db: Session = Depends(get_db)) -> list[dict]:
    entries = db.scalars(
        select(JournalEntry)
        .where(JournalEntry.organization_id == org_id)
        .order_by(JournalEntry.date.desc())
    ).all()
    return [
        {
            "id": e.id,
            "date": e.date.isoformat(),
            "memo": e.memo,
            "reference": e.reference,
            "source": e.source,
            "balanced": e.is_balanced,
            "total_debit": e.total_debit,
            "total_credit": e.total_credit,
            "lines": [
                {
                    "account_code": line.account.code,
                    "account_name": line.account.name,
                    "debit": line.debit,
                    "credit": line.credit,
                    "memo": line.memo,
                }
                for line in e.lines
            ],
        }
        for e in entries
    ]


@router.get("/orgs/{org_id}/reports/quickbooks.csv", response_class=PlainTextResponse)
def quickbooks_journal_csv(org_id: int, db: Session = Depends(get_db)) -> str:
    return quickbooks_csv.general_journal_csv(db, org_id)


@router.get("/orgs/{org_id}/reports/transactions.csv", response_class=PlainTextResponse)
def transactions_csv(org_id: int, db: Session = Depends(get_db)) -> str:
    return quickbooks_csv.transactions_csv(db, org_id)


@router.get("/orgs/{org_id}/reports/auditor.pdf")
def auditor_report(org_id: int, db: Session = Depends(get_db)) -> Response:
    pdf = auditor_pdf.build_auditor_report(db, org_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="mandate-treasury-report-{org_id}.pdf"'},
    )
