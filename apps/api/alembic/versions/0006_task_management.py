"""Create task management tables.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0006"
down_revision: str = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tasks ───────────────────────────────────────────────────────────────────
    # Enum types are auto-created by SQLAlchemy via op.create_table (same fix as 0001 userrole).
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.companies.id"),
            nullable=False,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "open", "in_progress", "blocked", "in_review", "done", "cancelled",
                name="task_status", schema="app",
            ),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "low", "medium", "high", "urgent", "critical",
                name="task_priority", schema="app",
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "task_type",
            sa.Enum(
                "general", "anomaly_response", "reorder", "approval", "review", "incident",
                name="task_type", schema="app",
            ),
            nullable=False,
            server_default="general",
        ),
        sa.Column(
            "source",
            sa.Enum(
                "manual", "ai_recommendation", "alert", "anomaly", "forecast", "schedule",
                name="task_source", schema="app",
            ),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_hours", sa.Integer, nullable=True),
        sa.Column("breached", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.create_index("ix_app_tasks_company_id", "tasks", ["company_id"], schema="app")
    op.create_index("ix_app_tasks_status", "tasks", ["status"], schema="app")

    # ── task_assignees ───────────────────────────────────────────────────────────
    op.create_table(
        "task_assignees",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_in_task",
            sa.Enum(
                "owner", "collaborator", "reviewer", "watcher",
                name="assignee_role", schema="app",
            ),
            nullable=False,
            server_default="collaborator",
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_assignee"),
        schema="app",
    )

    # ── task_departments ─────────────────────────────────────────────────────────
    op.create_table(
        "task_departments",
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.tasks.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("department", sa.Text, nullable=False, primary_key=True),
        schema="app",
    )

    # ── task_activity ────────────────────────────────────────────────────────────
    op.create_table(
        "task_activity",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "created", "status_changed", "assigned", "commented",
                "kpi_updated", "ai_suggested",
                name="activity_kind", schema="app",
            ),
            nullable=False,
        ),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="app",
    )
    op.create_index(
        "ix_app_task_activity_task_id", "task_activity", ["task_id"], schema="app"
    )

    # ── task_comments ────────────────────────────────────────────────────────────
    op.create_table(
        "task_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("app.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.create_index(
        "ix_app_task_comments_task_id", "task_comments", ["task_id"], schema="app"
    )


def downgrade() -> None:
    op.drop_index("ix_app_task_comments_task_id", table_name="task_comments", schema="app")
    op.drop_table("task_comments", schema="app")
    op.drop_index("ix_app_task_activity_task_id", table_name="task_activity", schema="app")
    op.drop_table("task_activity", schema="app")
    op.drop_table("task_departments", schema="app")
    op.drop_table("task_assignees", schema="app")
    op.drop_index("ix_app_tasks_status", table_name="tasks", schema="app")
    op.drop_index("ix_app_tasks_company_id", table_name="tasks", schema="app")
    op.drop_table("tasks", schema="app")
    op.execute("DROP TYPE app.activity_kind")
    op.execute("DROP TYPE app.assignee_role")
    op.execute("DROP TYPE app.task_source")
    op.execute("DROP TYPE app.task_type")
    op.execute("DROP TYPE app.task_priority")
    op.execute("DROP TYPE app.task_status")
