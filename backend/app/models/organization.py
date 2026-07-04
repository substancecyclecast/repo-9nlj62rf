"""Organization and treasury policy models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    legal_entity: Mapped[str] = mapped_column(String(255), default="")
    base_currency: Mapped[str] = mapped_column(String(16), default="USD")
    base_stablecoin: Mapped[str] = mapped_column(String(16), default="USDC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    policy: Mapped["TreasuryPolicy"] = relationship(
        back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )
    wallets = relationship("Wallet", back_populates="organization", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="organization", cascade="all, delete-orphan")
    contractors = relationship(
        "Contractor", back_populates="organization", cascade="all, delete-orphan"
    )


class TreasuryPolicy(Base):
    """Risk and automation policy that constrains the autonomous agent."""

    __tablename__ = "treasury_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), unique=True)

    # Reserves & rebalancing
    min_operating_reserve_usd: Mapped[float] = mapped_column(Float, default=50_000.0)
    target_stablecoin_pct: Mapped[float] = mapped_column(Float, default=0.85)
    idle_yield_threshold_usd: Mapped[float] = mapped_column(Float, default=100_000.0)
    target_yield_apy: Mapped[float] = mapped_column(Float, default=0.045)

    # Autonomy limits — above these the agent can only *propose*, never execute.
    max_autonomous_transfer_usd: Mapped[float] = mapped_column(Float, default=25_000.0)
    max_autonomous_daily_usd: Mapped[float] = mapped_column(Float, default=100_000.0)
    required_signatures: Mapped[int] = mapped_column(Integer, default=2)

    # Preferred settlement
    preferred_chain: Mapped[str] = mapped_column(String(32), default="base")
    auto_select_cheapest_chain: Mapped[bool] = mapped_column(default=True)

    organization: Mapped[Organization] = relationship(back_populates="policy")
