"""Add shared botanical reservations and execution lease ownership.

Revision ID: 20260908_0013
Revises: 20260907_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260908_0013"
down_revision: str | None = "20260907_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("lease_owner", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "pipeline_botanical_reservations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("candidate_key", sa.String(length=100), nullable=False),
        sa.Column("identity_key", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "domain in ('plants','discoveries')",
            name="ck_pipeline_botanical_reservations_domain",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identity_key",
            name="uq_pipeline_botanical_reservations_identity",
        ),
        sa.UniqueConstraint(
            "pipeline_run_id",
            "domain",
            "candidate_key",
            "identity_key",
            name="uq_pipeline_botanical_reservations_candidate_identity",
        ),
    )
    op.create_index(
        "ix_pipeline_botanical_reservations_run",
        "pipeline_botanical_reservations",
        ["pipeline_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pipeline_botanical_reservations_run",
        table_name="pipeline_botanical_reservations",
    )
    op.drop_table("pipeline_botanical_reservations")
    op.drop_column("pipeline_runs", "lease_owner")
