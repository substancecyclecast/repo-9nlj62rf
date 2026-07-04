"""Contractor, payroll batch, and payment models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Contractor(Base):
    """A payee: contractor, employee, or vendor."""

    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str] = mapped_column(String(255), default="")
    country: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(128), default="")

    payout_chain: Mapped[str] = mapped_column(String(32), default="base")
    payout_asset: Mapped[str] = mapped_column(String(32), default="USDC")
    wallet_address: Mapped[str] = mapped_column(String(128), default="")

    # Compliance status from KYC/AML provider (Bridge): pending|cleared|flagged
    kyc_status: Mapped[str] = mapped_column(String(32), default="pending")
    prefers_fiat: Mapped[bool] = mapped_column(default=False)

    organization = relationship("Organization", back_populates="contractors")


class PayrollBatch(Base):
    """A run of payments built from a CSV import or API request."""

    __tablename__ = "payroll_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|proposed|executed
    currency: Mapped[str] = mapped_column(String(16), default="USD")
    total_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_fees_usd: Mapped[float] = mapped_column(Float, default=0.0)
    payment_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class Payment(Base):
    """A single line in a payroll batch (one payee)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("payroll_batches.id"), index=True)
    contractor_id: Mapped[int | None] = mapped_column(ForeignKey("contractors.id"), nullable=True)

    payee_name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(64), default="")
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)
    chain: Mapped[str] = mapped_column(String(32), default="base")
    asset: Mapped[str] = mapped_column(String(32), default="USDC")
    to_address: Mapped[str] = mapped_column(String(128), default="")
    fee_usd: Mapped[float] = mapped_column(Float, default=0.0)
    route: Mapped[str] = mapped_column(String(64), default="")  # on-chain | off-ramp(fiat)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    memo: Mapped[str] = mapped_column(String(255), default="")

    batch: Mapped[PayrollBatch] = relationship(back_populates="payments")
