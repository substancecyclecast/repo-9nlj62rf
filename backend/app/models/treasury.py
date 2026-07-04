"""Wallet, transaction, and yield-position models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TxStatus, TxType
from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Wallet(Base):
    """A treasury wallet: a Safe (EVM) or Squads (Solana) multisig, or EOA."""

    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    label: Mapped[str] = mapped_column(String(255))
    chain: Mapped[str] = mapped_column(String(32), index=True)
    address: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="safe")  # safe | squads | eoa
    threshold: Mapped[int] = mapped_column(Integer, default=2)
    owners: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    organization = relationship("Organization", back_populates="wallets")
    balances: Mapped[list["WalletBalance"]] = relationship(
        back_populates="wallet", cascade="all, delete-orphan"
    )


class WalletBalance(Base):
    """Per-asset balance snapshot for a wallet."""

    __tablename__ = "wallet_balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), index=True)
    asset: Mapped[str] = mapped_column(String(32))
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    usd_price: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    wallet: Mapped[Wallet] = relationship(back_populates="balances")

    @property
    def usd_value(self) -> float:
        return round(self.amount * self.usd_price, 2)


class Transaction(Base):
    """A treasury movement at any lifecycle stage (draft → executed)."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    wallet_id: Mapped[int | None] = mapped_column(ForeignKey("wallets.id"), nullable=True)

    tx_type: Mapped[str] = mapped_column(String(32), default=TxType.PAYOUT, index=True)
    status: Mapped[str] = mapped_column(String(32), default=TxStatus.DRAFT, index=True)

    chain: Mapped[str] = mapped_column(String(32), default="base")
    asset: Mapped[str] = mapped_column(String(32), default="USDC")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    usd_value: Mapped[float] = mapped_column(Float, default=0.0)
    fee_usd: Mapped[float] = mapped_column(Float, default=0.0)

    counterparty: Mapped[str] = mapped_column(String(255), default="")
    to_address: Mapped[str] = mapped_column(String(128), default="")
    memo: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="uncategorized", index=True)

    tx_hash: Mapped[str] = mapped_column(String(128), default="")
    safe_tx_hash: Mapped[str] = mapped_column(String(128), default="")
    signatures: Mapped[int] = mapped_column(Integer, default=0)

    created_by: Mapped[str] = mapped_column(String(64), default="agent")
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("payroll_batches.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )


class YieldPosition(Base):
    """Idle treasury parked in a yield venue (Aave, Morpho, tokenized T-bills)."""

    __tablename__ = "yield_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    venue: Mapped[str] = mapped_column(String(64))  # aave_v3 | morpho | ondo_ousg
    chain: Mapped[str] = mapped_column(String(32), default="base")
    asset: Mapped[str] = mapped_column(String(32), default="USDC")
    principal_usd: Mapped[float] = mapped_column(Float, default=0.0)
    apy: Mapped[float] = mapped_column(Float, default=0.045)
    accrued_yield_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
