"""scenarios and scenario_runs tables for Scenario Planner."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.users.id"),
            nullable=False,
        ),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("baseline_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("share_token", sa.Text(), nullable=True, unique=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="app",
    )
    op.create_index("ix_scenarios_company", "scenarios", ["company_id"], schema="app")

    op.create_table(
        "scenario_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.users.id"),
            nullable=False,
        ),
        sa.Column("assumptions_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=False),
        sa.Column("run_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="app",
    )
    op.create_index("ix_scenario_runs_scenario", "scenario_runs", ["scenario_id"], schema="app")


def downgrade() -> None:
    op.drop_index("ix_scenario_runs_scenario", table_name="scenario_runs", schema="app")
    op.drop_table("scenario_runs", schema="app")
    op.drop_index("ix_scenarios_company", table_name="scenarios", schema="app")
    op.drop_table("scenarios", schema="app")
