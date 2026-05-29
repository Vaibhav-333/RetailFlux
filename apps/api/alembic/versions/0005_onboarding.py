"""Add onboarding_step INT to app.users.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-23 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "onboarding_step",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_step", schema="app")
