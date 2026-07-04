"""Agent run + step models — a full audit trail of every autonomous action."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentRun(Base):
    """One invocation of the CFO agent (a goal + its execution trace)."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="completed")  # running|completed|failed
    provider: Mapped[str] = mapped_column(String(32), default="deterministic")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    steps: Mapped[list["AgentRunStep"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AgentRunStep.idx"
    )


class AgentRunStep(Base):
    """A single tool call within an agent run, with arguments and observation."""

    __tablename__ = "agent_run_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    idx: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(32), default="tool")  # thought | tool | result
    tool: Mapped[str] = mapped_column(String(64), default="")
    arguments_json: Mapped[str] = mapped_column(Text, default="{}")
    observation_json: Mapped[str] = mapped_column(Text, default="{}")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped[AgentRun] = relationship(back_populates="steps")
