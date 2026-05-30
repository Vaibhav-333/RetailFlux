"""Performance indexes for hot analytics query paths.

Disabled in this revision — some column refs differ from base migrations
on fresh DBs (e.g. task_activity has no company_id). Indexes can be added
separately via SQL after the schema is in place. Kept as a no-op to
preserve the migration chain.

Revision ID: 0014
Revises: 0013
"""

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
