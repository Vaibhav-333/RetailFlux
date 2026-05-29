"""Add explanations cache table for AI-generated explanations.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-23 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "explanations",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="app",
    )
    op.create_index(
        "ix_explanations_resource_id_version",
        "explanations",
        ["resource", "resource_id", "version"],
        schema="app",
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_explanations_resource_id_version", table_name="explanations", schema="app")
    op.drop_table("explanations", schema="app")
