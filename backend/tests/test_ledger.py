"""Double-entry ledger invariants."""

from __future__ import annotations

import pytest

from app.services import ledger_service


def test_seed_books_are_balanced(db, org):
    tb = ledger_service.trial_balance(db, org.id)
    total_debit = round(sum(r["debit"] for r in tb), 2)
    total_credit = round(sum(r["credit"] for r in tb), 2)
    assert total_debit == total_credit
    assert total_debit > 0


def test_post_entry_rejects_unbalanced(db, org):
    with pytest.raises(ledger_service.UnbalancedEntryError):
        ledger_service.post_entry(
            db,
            organization_id=org.id,
            lines=[("1000", 100.0, 0.0), ("4000", 0.0, 90.0)],
            memo="bad entry",
        )


def test_post_entry_balanced_updates_trial_balance(db, org):
    before = ledger_service.income_statement(db, org.id)["revenue"]
    ledger_service.post_entry(
        db,
        organization_id=org.id,
        lines=[("1000", 1000.0, 0.0), ("4000", 0.0, 1000.0)],
        memo="extra revenue",
    )
    after = ledger_service.income_statement(db, org.id)["revenue"]
    assert round(after - before, 2) == 1000.0


def test_chart_of_accounts_idempotent(db, org):
    a = ledger_service.ensure_chart_of_accounts(db, org.id)
    b = ledger_service.ensure_chart_of_accounts(db, org.id)
    assert set(a.keys()) == set(b.keys())
