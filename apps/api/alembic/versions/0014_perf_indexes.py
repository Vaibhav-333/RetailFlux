"""Performance indexes for hot analytics query paths.

These indexes target the most common query patterns across tasks, uploads,
audit log, and task activity — the tables with the highest write rates in
production. Each index is created CONCURRENTLY to avoid locking.

Revision ID: 0014
Revises: 0013
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── app.tasks ─────────────────────────────────────────────────────────────
    # Hot path: list open tasks for a company, sorted by due date
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tasks_company_status_due
            ON app.tasks (company_id, status, due_at)
            WHERE deleted_at IS NULL;
        """
    )
    # Hot path: tasks assigned to a specific user
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_task_assignees_user
            ON app.task_assignees (user_id, task_id);
        """
    )
    # Hot path: analytics — count tasks by status/priority for a company
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tasks_company_priority
            ON app.tasks (company_id, priority, status)
            WHERE deleted_at IS NULL;
        """
    )

    # ── app.task_activity ─────────────────────────────────────────────────────
    # Hot path: activity stream per task, ordered by time
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_task_activity_task_created
            ON app.task_activity (task_id, created_at DESC);
        """
    )
    # Hot path: company-wide activity feed for analytics
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_task_activity_company_created
            ON app.task_activity (company_id, created_at DESC);
        """
    )

    # ── app.uploads ───────────────────────────────────────────────────────────
    # Hot path: list uploads for a company ordered by recency
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_uploads_company_created
            ON app.uploads (company_id, created_at DESC);
        """
    )

    # ── app.audit_log ─────────────────────────────────────────────────────────
    # Hot path: paginated audit log for admin view
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_audit_log_company_created
            ON app.audit_log (company_id, created_at DESC);
        """
    )

    # ── app.conversations / conversation_messages ─────────────────────────────
    # Hot path: list conversations for a user; retrieve messages for a thread
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_conversations_user_updated
            ON app.conversations (user_id, updated_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_conv_messages_conv_created
            ON app.conversation_messages (conversation_id, created_at ASC);
        """
    )

    # ── app.events (event log, created in 0016 but pre-declared here) ─────────
    # Skip: migration 0016 will create its own indexes at table-creation time.


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_tasks_company_status_due;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_task_assignees_user;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_tasks_company_priority;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_task_activity_task_created;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_task_activity_company_created;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_uploads_company_created;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_audit_log_company_created;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_conversations_user_updated;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS app.ix_conv_messages_conv_created;")
