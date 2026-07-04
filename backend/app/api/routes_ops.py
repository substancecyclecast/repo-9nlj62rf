"""Operational + billing endpoints: metrics, readiness, audit, webhooks, billing."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import settings
from app.core.database import get_db
from app.core.metrics import metrics
from app.services import audit_service, billing_service, webhooks

# Unprefixed router for infra probes that monitoring scrapers expect at the root.
infra_router = APIRouter(tags=["ops"])

# Prefixed router for tenant-scoped operational data.
router = APIRouter(tags=["ops"])


@infra_router.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics() -> str:
    return metrics.render_prometheus()


@infra_router.get("/healthz")
def liveness() -> dict:
    """Liveness probe — process is up."""
    return {"status": "ok", "service": "mandate", "version": __version__}


@infra_router.get("/readyz")
def readiness(db: Session = Depends(get_db)) -> dict:
    """Readiness probe — process is up *and* the database is reachable."""
    checks: dict[str, str] = {}
    ready = True
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - failure path
        checks["database"] = f"error: {exc}"
        ready = False
    return {
        "ready": ready,
        "version": __version__,
        "environment": settings.environment,
        "integration_mode": settings.integration_mode,
        "checks": checks,
    }


@router.get("/orgs/{org_id}/audit")
def list_audit(org_id: int, limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    return audit_service.list_for_org(db, org_id, limit=limit)


@router.get("/orgs/{org_id}/webhooks/deliveries")
def list_webhook_deliveries(org_id: int, limit: int = 50, db: Session = Depends(get_db)) -> list[dict]:
    return webhooks.list_for_org(db, org_id, limit=limit)


@router.post("/orgs/{org_id}/webhooks/test")
def test_webhook(org_id: int, db: Session = Depends(get_db)) -> dict:
    deliveries = webhooks.emit(
        db,
        event="webhook.test",
        summary="Test notification from Mandate",
        organization_id=org_id,
        fields={"triggered_by": "billing/settings page"},
        commit=True,
    )
    return {"delivered": [webhooks.serialize(d) for d in deliveries]}


@router.get("/orgs/{org_id}/billing/summary")
def billing_summary(org_id: int, db: Session = Depends(get_db)) -> dict:
    return billing_service.summary(db, org_id)


@router.get("/orgs/{org_id}/billing/invoice")
def billing_invoice(org_id: int, db: Session = Depends(get_db)) -> dict:
    return billing_service.invoice(db, org_id)
