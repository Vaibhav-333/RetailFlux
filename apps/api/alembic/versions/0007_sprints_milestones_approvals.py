"""Add sprints, milestones and task_approvals tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0007"
down_revision: str = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── milestones ───────────────────────────────────────────────────────────
    op.create_table(
        "milestones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.companies.id"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("app.users.id"),
            nullable=False,
        ),
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
    op.create_index(
        "ix_app_milestones_company_id", "milestones", ["company_id"], schema="app"
    )

    # ── sprints ──────────────────────────────────────────────────────────────
    op.create_table(
        "sprints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.companies.id"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("goal", sa.Text, nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="planning",
        ),
        sa.Column(
            "capacity_hours",
            sa.Numeric(7, 1),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("app.users.id"),
            nullable=False,
        ),
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
    op.create_index(
        "ix_app_sprints_company_id", "sprints", ["company_id"], schema="app"
    )

    # ── sprint_tasks ─────────────────────────────────────────────────────────
    op.create_table(
        "sprint_tasks",
        sa.Column(
            "sprint_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.sprints.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.tasks.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="app",
    )

    # ── task_approvals ───────────────────────────────────────────────────────
    op.create_table(
        "task_approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "approver_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.users.id"),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            UUID(as_uuid=True),
            sa.ForeignKey("app.users.id"),
            nullable=False,
        ),
        sa.Column("decision", sa.Text, nullable=True),  # 'approved' | 'rejected' | NULL (pending)
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="app",
    )
    op.create_index(
        "ix_app_task_approvals_task_id", "task_approvals", ["task_id"], schema="app"
    )
    op.create_index(
        "ix_app_task_approvals_approver_id",
        "task_approvals",
        ["approver_id"],
        schema="app",
    )

    # ── add milestone_id FK to tasks ─────────────────────────────────────────
    op.add_column(
        "tasks",
        sa.Column(
            "milestone_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.milestones.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("tasks", "milestone_id", schema="app")
    op.drop_index(
        "ix_app_task_approvals_approver_id",
        table_name="task_approvals",
        schema="app",
    )
    op.drop_index(
        "ix_app_task_approvals_task_id",
        table_name="task_approvals",
        schema="app",
    )
    op.drop_table("task_approvals", schema="app")
    op.drop_table("sprint_tasks", schema="app")
    op.drop_index("ix_app_sprints_company_id", table_name="sprints", schema="app")
    op.drop_table("sprints", schema="app")
    op.drop_index("ix_app_milestones_company_id", table_name="milestones", schema="app")
    op.drop_table("milestones", schema="app")
