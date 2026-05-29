"""Create inventory intelligence tables.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0008"
down_revision: str = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── suppliers ─────────────────────────────────────────────────────────────
    op.create_table(
        "suppliers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.companies.id"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("contact_email", sa.Text, nullable=True),
        sa.Column("lead_days_target", sa.Integer, nullable=True),
        sa.Column("otd_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("defect_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("tier", sa.Text, nullable=True),
        sa.Column("attributes", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="app",
    )
    op.create_index("ix_app_suppliers_company_id", "suppliers", ["company_id"], schema="app")

    # ── sku_master ────────────────────────────────────────────────────────────
    op.create_table(
        "sku_master",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.companies.id"),
            nullable=False,
        ),
        sa.Column("sku", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("category", sa.Text, nullable=True),
        sa.Column("subcategory", sa.Text, nullable=True),
        sa.Column("brand", sa.Text, nullable=True),
        sa.Column("season", sa.Text, nullable=True),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("abc_class", sa.String(1), nullable=True),
        sa.Column("xyz_class", sa.String(1), nullable=True),
        sa.Column("lifecycle_stage", sa.Text, nullable=True),
        sa.Column("launched_at", sa.Date, nullable=True),
        sa.Column("last_sold_at", sa.Date, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("attributes", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("company_id", "sku", name="uq_sku_master_company_sku"),
        schema="app",
    )
    op.create_index("ix_app_sku_master_company_id", "sku_master", ["company_id"], schema="app")
    op.create_index("ix_app_sku_master_sku", "sku_master", ["sku"], schema="app")
    op.create_index("ix_app_sku_master_abc_class", "sku_master", ["abc_class"], schema="app")

    # ── sku_suppliers (many-to-many) ──────────────────────────────────────────
    op.create_table(
        "sku_suppliers",
        sa.Column(
            "sku_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.sku_master.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "supplier_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.suppliers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("lead_days", sa.Integer, nullable=True),
        schema="app",
    )


def downgrade() -> None:
    op.drop_table("sku_suppliers", schema="app")
    op.drop_index("ix_app_sku_master_abc_class", table_name="sku_master", schema="app")
    op.drop_index("ix_app_sku_master_sku", table_name="sku_master", schema="app")
    op.drop_index("ix_app_sku_master_company_id", table_name="sku_master", schema="app")
    op.drop_table("sku_master", schema="app")
    op.drop_index("ix_app_suppliers_company_id", table_name="suppliers", schema="app")
    op.drop_table("suppliers", schema="app")
