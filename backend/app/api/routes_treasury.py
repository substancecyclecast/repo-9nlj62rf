"""Treasury, wallet, and organization endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Organization
from app.services import treasury_service

router = APIRouter(tags=["treasury"])


@router.get("/orgs")
def list_orgs(db: Session = Depends(get_db)) -> list[dict]:
    orgs = db.scalars(select(Organization).order_by(Organization.id)).all()
    return [
        {"id": o.id, "name": o.name, "slug": o.slug, "legal_entity": o.legal_entity}
        for o in orgs
    ]


@router.get("/orgs/{org_id}/overview")
def overview(org_id: int, db: Session = Depends(get_db)) -> dict:
    return treasury_service.overview(db, org_id)


@router.get("/orgs/{org_id}/wallets")
def wallets(org_id: int, db: Session = Depends(get_db)) -> list[dict]:
    return treasury_service.wallet_balances(db, org_id)


@router.get("/orgs/{org_id}/yield")
def yield_positions(org_id: int, db: Session = Depends(get_db)) -> list[dict]:
    return treasury_service.yield_positions(db, org_id)


@router.get("/orgs/{org_id}/recommendations")
def recommendations(org_id: int, db: Session = Depends(get_db)) -> list[dict]:
    return treasury_service.policy_recommendations(db, org_id)
