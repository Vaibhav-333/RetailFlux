"""Pricing & Profit Intelligence — add purchase_order lifecycle states index.

Session 35: The purchase_orders table already exists (0009). This migration
adds a compound index on (company_id, status, created_at) for efficient
approval-queue queries and a `po_number` text column for human-readable IDs.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-25
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add po_number column for human-readable PO identifiers
    op.execute("""
        ALTER TABLE app.purchase_orders
        ADD COLUMN IF NOT EXISTS po_number TEXT GENERATED ALWAYS AS (
            'PO-' || UPPER(SUBSTRING(id::text, 1, 8))
        ) STORED
    """)

    # Compound index: company + status + created_at (approval queue pattern)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_purchase_orders_company_status_created
        ON app.purchase_orders(company_id, status, created_at DESC)
    """)

    # Index for approved POs by approver
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_purchase_orders_approved_by
        ON app.purchase_orders(approved_by)
        WHERE approved_by IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.ix_purchase_orders_approved_by")
    op.execute("DROP INDEX IF EXISTS app.ix_purchase_orders_company_status_created")
    op.execute("ALTER TABLE app.purchase_orders DROP COLUMN IF EXISTS po_number")
