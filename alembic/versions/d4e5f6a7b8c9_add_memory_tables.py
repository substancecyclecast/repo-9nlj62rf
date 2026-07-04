"""add persistent memory tables (MemoryAgent)

company_profiles / supplier_memory / lot_decision_memory

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.CHAR(length=36), primary_key=True),
        sa.Column("customer_id", sa.CHAR(length=36), nullable=False),
        sa.Column("weight_price", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("weight_lead_time", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("weight_quality", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("preferred_regions", sa.JSON(), nullable=True),
        sa.Column("blacklisted_inns", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("lots_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("customer_id", name="uq_company_profiles_customer_id"),
    )
    op.create_index("ix_company_profiles_customer_id", "company_profiles", ["customer_id"], unique=True)

    op.create_table(
        "supplier_memory",
        sa.Column("id", sa.CHAR(length=36), primary_key=True),
        sa.Column("customer_id", sa.CHAR(length=36), nullable=False),
        sa.Column("inn", sa.String(length=20), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("times_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("times_selected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("on_time_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("avg_quality", sa.Float(), nullable=True),
        sa.Column("last_price_rub", sa.Numeric(15, 2), nullable=True),
        sa.Column("last_category", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_supplier_memory_customer_id", "supplier_memory", ["customer_id"], unique=False)
    op.create_index("ix_supplier_memory_inn", "supplier_memory", ["inn"], unique=False)

    op.create_table(
        "lot_decision_memory",
        sa.Column("id", sa.CHAR(length=36), primary_key=True),
        sa.Column("customer_id", sa.CHAR(length=36), nullable=False),
        sa.Column("lot_id", sa.CHAR(length=36), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=True),
        sa.Column("chosen_supplier_inn", sa.String(length=20), nullable=True),
        sa.Column("chosen_supplier_name", sa.String(length=255), nullable=True),
        sa.Column("total_rub", sa.Numeric(15, 2), nullable=True),
        sa.Column("savings_pct", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_lot_decision_memory_customer_id", "lot_decision_memory", ["customer_id"], unique=False)
    op.create_index("ix_lot_decision_memory_category", "lot_decision_memory", ["category"], unique=False)
    op.create_index("ix_lot_decision_memory_created_at", "lot_decision_memory", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("lot_decision_memory")
    op.drop_table("supplier_memory")
    op.drop_table("company_profiles")
