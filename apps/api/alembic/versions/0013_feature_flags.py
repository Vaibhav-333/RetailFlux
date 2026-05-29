"""Feature flags table for gradual feature rollout per company."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # NULL company_id = global flag (applies to all companies unless overridden)
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["app.companies.id"],
            ondelete="CASCADE",
        ),
        schema="app",
    )

    # Partial unique indexes — NULL != NULL in standard unique constraints,
    # so we use two partial indexes to enforce uniqueness separately.
    op.execute("""
        CREATE UNIQUE INDEX uq_ff_global_key
        ON app.feature_flags(key)
        WHERE company_id IS NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_ff_company_key
        ON app.feature_flags(company_id, key)
        WHERE company_id IS NOT NULL
    """)

    op.create_index("ix_feature_flags_company", "feature_flags", ["company_id"], schema="app")
    op.create_index("ix_feature_flags_key", "feature_flags", ["key"], schema="app")


def downgrade() -> None:
    op.drop_index("ix_feature_flags_key", table_name="feature_flags", schema="app")
    op.drop_index("ix_feature_flags_company", table_name="feature_flags", schema="app")
    op.execute("DROP INDEX IF EXISTS app.uq_ff_company_key")
    op.execute("DROP INDEX IF EXISTS app.uq_ff_global_key")
    op.drop_table("feature_flags", schema="app")
