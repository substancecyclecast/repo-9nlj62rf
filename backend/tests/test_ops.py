"""Tests for observability, audit log, webhooks, billing, and rate limiting."""

from __future__ import annotations

import pytest

from app.core.metrics import MetricsRegistry
from app.services import audit_service, billing_service, payroll_service, webhooks

# --- Metrics registry ---

def test_metrics_counter_and_prometheus_render():
    reg = MetricsRegistry()
    reg.inc("mandate_test_total", method="GET")
    reg.inc("mandate_test_total", method="GET")
    reg.inc("mandate_test_total", method="POST")
    out = reg.render_prometheus()
    assert "# TYPE mandate_test_total counter" in out
    assert 'mandate_test_total{method="GET"} 2' in out
    assert 'mandate_test_total{method="POST"} 1' in out
    assert "mandate_uptime_seconds" in out


def test_metrics_histogram_render():
    reg = MetricsRegistry()
    reg.observe("mandate_latency_seconds", 0.003, route="/x")
    reg.observe("mandate_latency_seconds", 0.4, route="/x")
    out = reg.render_prometheus()
    assert "mandate_latency_seconds_bucket" in out
    assert "mandate_latency_seconds_count" in out
    assert 'le="+Inf"' in out


# --- Audit log ---

def test_audit_record_and_list(db, org):
    audit_service.record(
        db, organization_id=org.id, action="payroll.executed", resource="batch:1",
        detail={"total_usd": 1000}, commit=True,
    )
    rows = audit_service.list_for_org(db, org.id)
    assert len(rows) == 1
    assert rows[0]["action"] == "payroll.executed"
    assert rows[0]["detail"]["total_usd"] == 1000


# --- Webhooks (sandbox: skipped, but recorded) ---

def test_webhook_emit_records_outbox_when_unconfigured(db, org):
    deliveries = webhooks.emit(
        db, event="payroll.executed", summary="Settled 3 payments",
        organization_id=org.id, fields={"total_usd": 500}, commit=True,
    )
    assert deliveries
    assert deliveries[0].status == "skipped"
    listed = webhooks.list_for_org(db, org.id)
    assert listed[0]["event"] == "payroll.executed"


# --- Billing ---

def test_billing_summary_reflects_executed_volume(db, org):
    rows = [
        {"name": "Ada", "country": "NG", "amount_usd": 1000, "payout_asset": "USDC"},
        {"name": "Ben", "country": "DE", "amount_usd": 2000, "payout_asset": "EURC"},
    ]
    batch = payroll_service.build_plan(db, organization_id=org.id, name="b", rows=rows)
    payroll_service.propose_batch(db, batch_id=batch.id)
    payroll_service.execute_batch(db, batch_id=batch.id)
    db.commit()

    s = billing_service.summary(db, org.id)
    assert s["settled_volume_usd"] == pytest.approx(3000.0)
    assert s["take_rate_bps"] == 25
    assert s["mtd_take_rate_usd"] == pytest.approx(3000.0 * 25 / 10_000)
    assert s["estimated_mrr_usd"] >= s["platform_fee_usd"]

    inv = billing_service.invoice(db, org.id)
    assert inv["total_usd"] == pytest.approx(s["current_invoice_usd"])
    assert len(inv["line_items"]) == 2


# --- Rate limiting middleware ---

def test_rate_limit_middleware_blocks_over_limit():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from app.core import middleware as mw
    from app.core.config import settings

    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/ping", ok)])
    app.add_middleware(mw.RateLimitMiddleware, limit=3, window_seconds=60)

    settings.rate_limit_enabled = True
    try:
        client = TestClient(app)
        codes = [client.get("/ping").status_code for _ in range(5)]
    finally:
        settings.rate_limit_enabled = False

    assert codes[:3] == [200, 200, 200]
    assert 429 in codes[3:]


def test_health_exempt_from_rate_limit():
    from app.core import middleware as mw

    assert "/healthz" in mw.RateLimitMiddleware.EXEMPT_PREFIXES
    assert "/metrics" in mw.RateLimitMiddleware.EXEMPT_PREFIXES
