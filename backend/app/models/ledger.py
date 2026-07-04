"""Double-entry accounting models: chart of accounts, journal entries, lines."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import AccountType
from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    """A node in the double-entry chart of accounts."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(32), default=AccountType.ASSET)

    organization = relationship("Organization", back_populates="accounts")
    lines: Mapped[list["JournalLine"]] = relationship(back_populates="account")

    @property
    def is_debit_normal(self) -> bool:
        return self.type in (AccountType.ASSET, AccountType.EXPENSE)


class JournalEntry(Base):
    """A balanced set of debit/credit lines representing one economic event."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    memo: Mapped[str] = mapped_column(Text, default="")
    reference: Mapped[str] = mapped_column(String(128), default="")
    source: Mapped[str] = mapped_column(String(64), default="agent")  # agent | manual | import

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )

    @property
    def total_debit(self) -> float:
        return round(sum(line.debit for line in self.lines), 2)

    @property
    def total_credit(self) -> float:
        return round(sum(line.credit for line in self.lines), 2)

    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debit - self.total_credit) < 0.005


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    debit: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[float] = mapped_column(Float, default=0.0)
    memo: Mapped[str] = mapped_column(String(255), default="")

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship(back_populates="lines")
