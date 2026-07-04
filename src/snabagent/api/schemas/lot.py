from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LotStatusEnum(str, Enum):
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


class LotCreateIn(BaseModel):
    customer_name: str = "SIBUR Demo"
    raw_request: str
    requester_email: str | None = None
    attachments: list[str] = Field(default_factory=list)
    phase: str = "pre_nmck"
    total_estimated_rub: float | None = None
    external_ref: str | None = None


class LotListItem(BaseModel):
    id: UUID
    status: LotStatusEnum
    category: str | None
    raw_request_preview: str
    created_at: datetime
    requires_human: bool


class LotDetailOut(BaseModel):
    id: UUID
    status: LotStatusEnum
    phase: str | None
    category: str | None
    raw_request: str
    parsed_items: list[dict] = Field(default_factory=list)
    final_report: dict[str, Any] | None
    requires_human: bool
    escalation_reason: str | None
    created_at: datetime
    updated_at: datetime


class PaginatedLots(BaseModel):
    items: list[LotListItem]
    total: int
    page: int
    page_size: int
    pages: int


class LotApproveIn(BaseModel):
    supplier_id: UUID | None = None
    reviewer_name: str | None = None
    comment: str | None = None
