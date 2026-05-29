"""purchase_orders and po_lines for auto-replenishment (Session 33).

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-24
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE app.purchase_orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES app.companies(id),
            status TEXT NOT NULL DEFAULT 'draft',
            supplier_name TEXT,
            total_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
            notes TEXT,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_by UUID REFERENCES app.users(id),
            approved_by UUID REFERENCES app.users(id),
            approved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE app.po_lines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            po_id UUID NOT NULL REFERENCES app.purchase_orders(id) ON DELETE CASCADE,
            sku TEXT NOT NULL,
            quantity NUMERIC(12, 2) NOT NULL DEFAULT 0,
            unit_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_purchase_orders_company_id ON app.purchase_orders(company_id)")
    op.execute("CREATE INDEX ix_purchase_orders_status ON app.purchase_orders(status)")
    op.execute("CREATE INDEX ix_po_lines_po_id ON app.po_lines(po_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.ix_po_lines_po_id")
    op.execute("DROP INDEX IF EXISTS app.ix_purchase_orders_status")
    op.execute("DROP INDEX IF EXISTS app.ix_purchase_orders_company_id")
    op.execute("DROP TABLE IF EXISTS app.po_lines")
    op.execute("DROP TABLE IF EXISTS app.purchase_orders")
