"""QuickBooks-compatible CSV exports.

Two exports:
* ``general_journal_csv`` — debits/credits per journal line (QuickBooks "General
  Journal" import format).
* ``transactions_csv`` — flat transaction register for spreadsheets.
"""

from __future__ import annotations

import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JournalEntry, Transaction
from app.services import ledger_service


def general_journal_csv(db: Session, organization_id: int) -> str:
    entries = db.scalars(
        select(JournalEntry)
        .where(JournalEntry.organization_id == organization_id)
        .order_by(JournalEntry.date)
    ).all()
    accounts = {a.id: a for a in ledger_service.ensure_chart_of_accounts(db, organization_id).values()}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["JournalNo", "Date", "Account", "Debit", "Credit", "Memo", "Reference"])
    for e in entries:
        for line in e.lines:
            acc = accounts.get(line.account_id) or line.account
            writer.writerow(
                [
                    e.id,
                    e.date.strftime("%Y-%m-%d"),
                    f"{acc.code} {acc.name}",
                    f"{line.debit:.2f}" if line.debit else "",
                    f"{line.credit:.2f}" if line.credit else "",
                    line.memo or e.memo,
                    e.reference,
                ]
            )
    return buf.getvalue()


def transactions_csv(db: Session, organization_id: int) -> str:
    txs = db.scalars(
        select(Transaction)
        .where(Transaction.organization_id == organization_id)
        .order_by(Transaction.created_at)
    ).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Date", "Type", "Status", "Counterparty", "Category", "Chain",
            "Asset", "Amount", "USD", "Fee USD", "ToAddress", "TxHash", "Memo",
        ]
    )
    for t in txs:
        writer.writerow(
            [
                t.created_at.strftime("%Y-%m-%d %H:%M"),
                t.tx_type,
                t.status,
                t.counterparty,
                t.category,
                t.chain,
                t.asset,
                f"{t.amount:.4f}",
                f"{t.usd_value:.2f}",
                f"{t.fee_usd:.2f}",
                t.to_address,
                t.tx_hash,
                t.memo,
            ]
        )
    return buf.getvalue()
