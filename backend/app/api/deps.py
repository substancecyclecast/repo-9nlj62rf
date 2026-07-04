"""Shared API dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Organization


def get_organization(org_id: int, db: Session = Depends(get_db)) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail=f"Organization {org_id} not found")
    return org


def default_org_id(db: Session) -> int:
    org = db.scalar(select(Organization).order_by(Organization.id))
    if org is None:
        raise HTTPException(status_code=404, detail="No organizations exist; seed the demo first")
    return org.id
