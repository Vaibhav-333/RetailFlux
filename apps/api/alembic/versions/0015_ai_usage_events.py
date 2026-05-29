"""ai_usage tracking table.

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS app.ai_usage (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id      UUID REFERENCES app.companies(id) ON DELETE SET NULL,
            user_id         UUID REFERENCES app.users(id) ON DELETE SET NULL,
            provider        TEXT NOT NULL,
            model           TEXT NOT NULL,
            endpoint        TEXT,
            tokens_in       INTEGER,
            tokens_out      INTEGER,
            latency_ms      INTEGER,
            cost_estimate_usd NUMERIC(10, 6),
            cache_hit       BOOLEAN NOT NULL DEFAULT false,
            error           TEXT,
            occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ai_usage_company_date
            ON app.ai_usage(company_id, occurred_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ai_usage_provider
            ON app.ai_usage(provider, occurred_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.ix_ai_usage_provider")
    op.execute("DROP INDEX IF EXISTS app.ix_ai_usage_company_date")
    op.execute("DROP TABLE IF EXISTS app.ai_usage")
