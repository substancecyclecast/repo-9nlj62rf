"""Add Row-Level Security policies for multi-tenant isolation.

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS on tenant-scoped tables
    tables_with_customer_id = ["lots", "nsi_items", "suppliers", "negotiations", "verifications", "rfq_emails"]

    for table in tables_with_customer_id:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

        # Policy: app role can only see rows matching current_setting('app.customer_id')
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            FOR ALL
            USING (customer_id::text = current_setting('app.customer_id', true))
            WITH CHECK (customer_id::text = current_setting('app.customer_id', true));
        """)

        # Policy: superuser/admin bypass (for migrations, maintenance)
        op.execute(f"""
            CREATE POLICY admin_bypass_{table} ON {table}
            FOR ALL
            TO snab_admin
            USING (true)
            WITH CHECK (true);
        """)

    # Add email_verified and email_verify_token columns to users
    op.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verify_token VARCHAR(64);
    """)


def downgrade() -> None:
    tables_with_customer_id = ["lots", "nsi_items", "suppliers", "negotiations", "verifications", "rfq_emails"]

    for table in tables_with_customer_id:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_{table} ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verify_token;")
