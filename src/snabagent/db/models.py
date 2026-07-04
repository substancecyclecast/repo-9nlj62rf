"""SQLAlchemy 2.x async-модели.

Используется JSON-колонка (sqlalchemy.JSON) вместо PG-специфичных типов,
чтобы модели работали как на PostgreSQL (prod), так и на SQLite (offline-демо / тесты).
"""
from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import DateTime as _DateTime
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, TypeDecorator

# Use timezone-aware DateTime for PostgreSQL compatibility
DateTime = _DateTime(timezone=True)


class UUIDStr(TypeDecorator):
    """Универсальный UUID-тип: на Postgres использует TEXT (UUID можно конвертировать), на SQLite — TEXT."""

    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ARG002
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):  # noqa: ARG002
        if value is None:
            return None
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            return value


class Base(DeclarativeBase):
    pass


class LotStatus(str, enum.Enum):
    draft = "draft"
    planned = "planned"
    sourcing = "sourcing"
    rfq_sent = "rfq_sent"
    responses_collected = "responses_collected"
    negotiating = "negotiating"
    verified = "verified"
    report_ready = "report_ready"
    approved = "approved"
    rejected = "rejected"
    escalated = "escalated"
    failed = "failed"


class ProcurementPhase(str, enum.Enum):
    pre_nmck = "pre_nmck"
    post_tender_published = "post_tender_published"
    unregulated = "unregulated"


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    inn: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    # Trial / lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    trial_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserRole(str, enum.Enum):
    admin = "admin"        # full access, может одобрять >1M, видит всех customer'ов
    buyer = "buyer"        # создаёт лоты, одобряет лимит < approval_limit
    viewer = "viewer"      # только просмотр


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    customer_id: Mapped[UUID | None] = mapped_column(
        UUIDStr, ForeignKey("customers.id", ondelete="SET NULL"), index=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.buyer)
    approval_limit_rub: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verify_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class NsiItem(Base):
    __tablename__ = "nsi_items"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(UUIDStr, ForeignKey("customers.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40), index=True)
    unit: Mapped[str | None] = mapped_column(String(20))
    gost: Mapped[str | None] = mapped_column(String(80))
    typical_price_rub: Mapped[float | None] = mapped_column(Numeric(15, 2))
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    embedding_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    inn: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    ogrn: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str | None] = mapped_column(String(120))
    legal_address: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(String(255))
    okved_codes: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    categories: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    region: Mapped[str | None] = mapped_column(String(64))
    avg_response_time_hours: Mapped[int | None] = mapped_column(Integer)
    historical_score: Mapped[float | None] = mapped_column(Float)
    spark_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    source: Mapped[str | None] = mapped_column(String(40))
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Lot(Base):
    __tablename__ = "lots"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(UUIDStr, ForeignKey("customers.id"), index=True)
    external_ref: Mapped[str | None] = mapped_column(String(80))
    requester_email: Mapped[str | None] = mapped_column(String(255))
    raw_request: Mapped[str] = mapped_column(Text)
    phase: Mapped[ProcurementPhase] = mapped_column(SAEnum(ProcurementPhase), default=ProcurementPhase.pre_nmck)
    category: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[LotStatus] = mapped_column(SAEnum(LotStatus), default=LotStatus.draft, index=True)
    total_estimated_rub: Mapped[float | None] = mapped_column(Numeric(15, 2))
    nmck_rub: Mapped[float | None] = mapped_column(Numeric(15, 2))
    parsed_items: Mapped[list | None] = mapped_column(JSON, default=list)
    chosen_supplier_id: Mapped[UUID | None] = mapped_column(UUIDStr, ForeignKey("suppliers.id"), nullable=True)
    final_report: Mapped[dict | None] = mapped_column(JSON, default=dict)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    audit_events: Mapped[list[AuditLog]] = relationship(
        back_populates="lot", cascade="all, delete-orphan", order_by="AuditLog.created_at"
    )
    rfq_emails: Mapped[list[RfqEmail]] = relationship(back_populates="lot", cascade="all, delete-orphan")


class RfqEmail(Base):
    __tablename__ = "rfq_emails"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    # nullable: IMAP-поллер сначала пишет письмо, потом маршрутизирует по Subject/To
    lot_id: Mapped[UUID | None] = mapped_column(
        UUIDStr, ForeignKey("lots.id", ondelete="CASCADE"), index=True, nullable=True
    )
    supplier_id: Mapped[UUID | None] = mapped_column(UUIDStr, ForeignKey("suppliers.id"))
    direction: Mapped[str] = mapped_column(String(10))
    subject: Mapped[str | None] = mapped_column(String(500))
    body_text: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)
    message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(255))
    references_ids: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    attachments: Mapped[list[dict] | None] = mapped_column(JSON, default=list)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    received_at: Mapped[datetime | None] = mapped_column(DateTime)
    parsed_offer: Mapped[dict | None] = mapped_column(JSON, default=dict)
    raw_email_path: Mapped[str | None] = mapped_column(String(500))

    lot: Mapped[Lot] = relationship(back_populates="rfq_emails")


class Negotiation(Base):
    __tablename__ = "negotiations"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    lot_id: Mapped[UUID] = mapped_column(UUIDStr, ForeignKey("lots.id", ondelete="CASCADE"))
    supplier_id: Mapped[UUID | None] = mapped_column(UUIDStr, ForeignKey("suppliers.id"))
    round_no: Mapped[int] = mapped_column(Integer, default=1)
    initial_offer: Mapped[dict | None] = mapped_column(JSON, default=dict)
    target_discount_pct: Mapped[float | None] = mapped_column(Float)
    final_offer: Mapped[dict | None] = mapped_column(JSON, default=dict)
    delta_pct: Mapped[float | None] = mapped_column(Float)
    allowed_by_filter: Mapped[bool] = mapped_column(Boolean, default=True)
    filter_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Verification(Base):
    __tablename__ = "verifications"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    lot_id: Mapped[UUID] = mapped_column(UUIDStr, ForeignKey("lots.id", ondelete="CASCADE"))
    supplier_id: Mapped[UUID | None] = mapped_column(UUIDStr, ForeignKey("suppliers.id"))
    inn_valid: Mapped[bool | None] = mapped_column(Boolean)
    ogrn_valid: Mapped[bool | None] = mapped_column(Boolean)
    spark_match: Mapped[bool | None] = mapped_column(Boolean)
    price_consistent: Mapped[bool | None] = mapped_column(Boolean)
    lead_time_meets_spec: Mapped[bool | None] = mapped_column(Boolean)
    gost_match: Mapped[bool | None] = mapped_column(Boolean)
    discrepancies: Mapped[list[dict] | None] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    verifier_model: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    lot_id: Mapped[UUID] = mapped_column(UUIDStr, ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    agent_name: Mapped[str] = mapped_column(String(40), index=True)
    step_name: Mapped[str] = mapped_column(String(80))
    input_payload: Mapped[dict | None] = mapped_column(JSON, default=dict)
    output_payload: Mapped[dict | None] = mapped_column(JSON, default=dict)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    llm_response_raw: Mapped[dict | None] = mapped_column(JSON, default=dict)
    model_name: Mapped[str | None] = mapped_column(String(120))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[str | None] = mapped_column(String(40))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)

    lot: Mapped[Lot] = relationship(back_populates="audit_events")


class HistoricalPurchase(Base):
    __tablename__ = "historical_purchases"
    id: Mapped[UUID] = mapped_column(UUIDStr, primary_key=True, default=uuid4)
    customer_id: Mapped[UUID | None] = mapped_column(UUIDStr, ForeignKey("customers.id"))
    supplier_id: Mapped[UUID | None] = mapped_column(UUIDStr, ForeignKey("suppliers.id"))
    nsi_sku: Mapped[str | None] = mapped_column(String(80), index=True)
    qty: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(20))
    price_rub: Mapped[float | None] = mapped_column(Numeric(15, 2))
    purchase_date: Mapped[str | None] = mapped_column(String(20))
    on_time: Mapped[bool | None] = mapped_column(Boolean)
    quality_score: Mapped[float | None] = mapped_column(Float)
