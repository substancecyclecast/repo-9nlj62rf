"""Double-entry accounting service.

Every economic event posts a balanced journal entry (sum of debits == sum of
credits). The service enforces that invariant and provides the primitives the
agent and API use to keep the books auditor-ready.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_CHART_OF_ACCOUNTS, AccountType
from app.models import Account, JournalEntry, JournalLine


class UnbalancedEntryError(ValueError):
    """Raised when a journal entry's debits and credits do not match."""


def ensure_chart_of_accounts(db: Session, organization_id: int) -> dict[str, Account]:
    """Idempotently seed and return the org's chart of accounts keyed by code."""
    existing = {
        a.code: a
        for a in db.scalars(
            select(Account).where(Account.organization_id == organization_id)
        ).all()
    }
    for code, name, acc_type in DEFAULT_CHART_OF_ACCOUNTS:
        if code not in existing:
            acc = Account(
                organization_id=organization_id, code=code, name=name, type=acc_type
            )
            db.add(acc)
            existing[code] = acc
    db.flush()
    return existing


def get_account(db: Session, organization_id: int, code: str) -> Account:
    acc = db.scalar(
        select(Account).where(
            Account.organization_id == organization_id, Account.code == code
        )
    )
    if acc is None:
        raise ValueError(f"Account {code} not found for org {organization_id}")
    return acc


def post_entry(
    db: Session,
    *,
    organization_id: int,
    lines: list[tuple[str, float, float]],
    memo: str = "",
    reference: str = "",
    source: str = "agent",
    date: datetime | None = None,
) -> JournalEntry:
    """Post a balanced journal entry.

    ``lines`` is a list of ``(account_code, debit, credit)`` tuples. Raises
    :class:`UnbalancedEntryError` if debits != credits.
    """
    accounts = ensure_chart_of_accounts(db, organization_id)
    total_debit = round(sum(d for _, d, _ in lines), 2)
    total_credit = round(sum(c for _, _, c in lines), 2)
    if abs(total_debit - total_credit) >= 0.005:
        raise UnbalancedEntryError(
            f"Entry not balanced: debit {total_debit} != credit {total_credit}"
        )

    entry = JournalEntry(
        organization_id=organization_id, memo=memo, reference=reference, source=source
    )
    if date is not None:
        entry.date = date
    db.add(entry)
    db.flush()

    for code, debit, credit in lines:
        if code not in accounts:
            raise ValueError(f"Unknown account code: {code}")
        db.add(
            JournalLine(
                entry_id=entry.id,
                account_id=accounts[code].id,
                debit=round(debit, 2),
                credit=round(credit, 2),
                memo=memo[:255],
            )
        )
    db.flush()
    return entry


def trial_balance(db: Session, organization_id: int) -> list[dict]:
    """Return per-account debit/credit totals and signed balance."""
    accounts = db.scalars(
        select(Account).where(Account.organization_id == organization_id).order_by(Account.code)
    ).all()
    rows = []
    for acc in accounts:
        debit = round(sum(line.debit for line in acc.lines), 2)
        credit = round(sum(line.credit for line in acc.lines), 2)
        balance = debit - credit if acc.is_debit_normal else credit - debit
        rows.append(
            {
                "code": acc.code,
                "name": acc.name,
                "type": acc.type,
                "debit": debit,
                "credit": credit,
                "balance": round(balance, 2),
            }
        )
    return rows


def income_statement(db: Session, organization_id: int) -> dict:
    """Summarise revenue, expense, and net income from the trial balance."""
    tb = trial_balance(db, organization_id)
    revenue = round(sum(r["balance"] for r in tb if r["type"] == AccountType.REVENUE), 2)
    expense = round(sum(r["balance"] for r in tb if r["type"] == AccountType.EXPENSE), 2)
    return {
        "revenue": revenue,
        "expense": expense,
        "net_income": round(revenue - expense, 2),
        "revenue_accounts": [r for r in tb if r["type"] == AccountType.REVENUE],
        "expense_accounts": [r for r in tb if r["type"] == AccountType.EXPENSE],
    }
