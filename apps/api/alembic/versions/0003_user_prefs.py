"""Add prefs JSONB column to app.users.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-17 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "prefs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("users", "prefs", schema="app")
