"""Audit log enhancements (diff, request_id) + Row-Level Security policies.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-17 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Audit log enhancements ────────────────────────────────────────────────
    op.add_column("audit_log", sa.Column("diff", postgresql.JSONB(), nullable=True), schema="app")
    op.add_column(
        "audit_log", sa.Column("request_id", sa.String(64), nullable=True), schema="app"
    )
    op.create_index(
        "ix_app_audit_log_user_id", "audit_log", ["user_id"], schema="app"
    )
    op.create_index(
        "ix_app_audit_log_resource", "audit_log", ["resource"], schema="app"
    )
    op.create_index(
        "ix_app_audit_log_created_at", "audit_log", ["created_at"], schema="app"
    )

    # ── Row-Level Security policies ───────────────────────────────────────────
    # Enable RLS on all company-scoped tables.
    # The app sets `app.current_company_id` via SET LOCAL on each request's DB session.

    # Users table: user can only see users from their own company
    op.execute("ALTER TABLE app.users ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY company_isolation_users ON app.users
        USING (company_id = current_setting('app.current_company_id', true)::uuid)
    """)

    # Uploads table: user can only see uploads from their own company
    op.execute("ALTER TABLE app.uploads ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY company_isolation_uploads ON app.uploads
        USING (company_id = current_setting('app.current_company_id', true)::uuid)
    """)

    # Notifications table: user can only see their own notifications
    op.execute("ALTER TABLE app.notifications ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_isolation_notifications ON app.notifications
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
    """)

    # IMPORTANT: RLS does not apply to superuser or table owner by default.
    # For the app DB user, we FORCE RLS so it applies even to the table owner.
    op.execute("ALTER TABLE app.users FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.uploads FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.notifications FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    # Remove RLS
    op.execute("ALTER TABLE app.notifications DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS user_isolation_notifications ON app.notifications")
    op.execute("ALTER TABLE app.uploads DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS company_isolation_uploads ON app.uploads")
    op.execute("ALTER TABLE app.users DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS company_isolation_users ON app.users")

    # Remove audit columns
    op.drop_index("ix_app_audit_log_created_at", table_name="audit_log", schema="app")
    op.drop_index("ix_app_audit_log_resource", table_name="audit_log", schema="app")
    op.drop_index("ix_app_audit_log_user_id", table_name="audit_log", schema="app")
    op.drop_column("audit_log", "request_id", schema="app")
    op.drop_column("audit_log", "diff", schema="app")
