"""User and multi-tenancy models for authentication & RBAC."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Application user (linked to Privy identity)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # Privy user ID
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    wallet_address: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    memberships: Mapped[list["UserOrgMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserOrgMembership(Base):
    """Many-to-many relationship between users and organizations with role."""

    __tablename__ = "user_org_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="member")  # owner|admin|member|viewer
    invited_by: Mapped[str] = mapped_column(String(255), default="")
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="memberships")


class APIKey(Base):
    """API key for programmatic access (service accounts, agents)."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    role: Mapped[str] = mapped_column(String(32), default="agent")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
