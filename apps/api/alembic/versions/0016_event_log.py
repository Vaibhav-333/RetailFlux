"""Unified event log table for tasks + scenarios.

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS app.events (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id    UUID NOT NULL REFERENCES app.companies(id) ON DELETE CASCADE,
            kind          TEXT NOT NULL,
            payload       JSONB NOT NULL DEFAULT '{}',
            actor_id      UUID REFERENCES app.users(id) ON DELETE SET NULL,
            resource_type TEXT,
            resource_id   UUID,
            occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_events_company_kind
            ON app.events(company_id, kind)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_events_company_occurred
            ON app.events(company_id, occurred_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_events_resource
            ON app.events(resource_type, resource_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.ix_events_resource")
    op.execute("DROP INDEX IF EXISTS app.ix_events_company_occurred")
    op.execute("DROP INDEX IF EXISTS app.ix_events_company_kind")
    op.execute("DROP TABLE IF EXISTS app.events")
