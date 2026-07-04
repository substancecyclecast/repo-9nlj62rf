"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    goal: str = Field(..., examples=["Review the treasury and deploy idle cash to yield"])
    structured_calls: list[dict] | None = None


class AgentStepOut(BaseModel):
    idx: int
    kind: str
    tool: str
    message: str
    arguments: dict
    observation: dict


class AgentRunOut(BaseModel):
    id: int
    goal: str
    status: str
    provider: str
    summary: str
    steps: list[AgentStepOut]


class TransferRequest(BaseModel):
    to_address: str
    amount_usd: float
    asset: str = "USDC"
    chain: str = "base"
    counterparty: str = ""
    memo: str = ""
    category: str = "vendor"


class PayrollRow(BaseModel):
    name: str
    amount_usd: float
    email: str = ""
    country: str = ""
    role: str = ""
    chain: str = ""
    asset: str = "USDC"
    wallet_address: str = ""
    prefers_fiat: bool = False
    memo: str = ""


class PayrollJsonRequest(BaseModel):
    name: str = "API payroll batch"
    rows: list[PayrollRow]
    auto_execute: bool = False


class SwapRequest(BaseModel):
    from_asset: str = "USDC"
    to_asset: str = "USDT"
    amount: float
    from_chain: str = "base"
    to_chain: str = "base"


class DeployYieldRequest(BaseModel):
    amount_usd: float
    asset: str = "USDC"
    venue: str | None = None
