"""add customer_id index on lots

Revision ID: b1c2d3e4f5a6
Revises: 846f921fd198
Create Date: 2026-01-15
"""
from __future__ import annotations

import sqlalchemy as sa  # noqa: F401
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "846f921fd198"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_lots_customer_id", "lots", ["customer_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lots_customer_id", table_name="lots")
