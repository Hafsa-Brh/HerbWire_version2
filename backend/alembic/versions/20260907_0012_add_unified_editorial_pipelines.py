"""Add unified editorial generation pipeline state.

Revision ID: 20260907_0012
Revises: 20260907_0011
Create Date: 2026-09-07 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260907_0012"
down_revision: str | None = "20260907_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(
        "uq_pipeline_runs_one_active_plant_profile", table_name="pipeline_runs"
    )
    op.create_index(
        "uq_pipeline_runs_one_active_editorial_generation",
        "pipeline_runs",
        [sa.text("(1)")],
        unique=True,
        postgresql_where=sa.text(
            "status = 'running' AND pipeline_type IN "
            "('plant_profile_automation','discovery_article_automation',"
            "'pubmed_discovery_review')"
        ),
    )
    op.create_table(
        "discovery_pipeline_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_key", sa.String(100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "candidate_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "work_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("discovery_article_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('pending','running','succeeded','failed','held')",
            name="ck_discovery_pipeline_items_status",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["discovery_article_id"], ["discovery_articles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["review_id"], ["editorial_reviews.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_key", name="uq_discovery_pipeline_candidate_key"
        ),
        sa.UniqueConstraint(
            "pipeline_run_id", "position", name="uq_discovery_pipeline_items_position"
        ),
        sa.UniqueConstraint(
            "discovery_article_id", name="uq_discovery_pipeline_items_article"
        ),
        sa.UniqueConstraint("review_id", name="uq_discovery_pipeline_items_review"),
    )
    op.create_index(
        "ix_discovery_pipeline_items_run",
        "discovery_pipeline_items",
        ["pipeline_run_id"],
    )
    op.create_index(
        "ix_discovery_pipeline_items_status",
        "discovery_pipeline_items",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_discovery_pipeline_items_status", table_name="discovery_pipeline_items"
    )
    op.drop_index(
        "ix_discovery_pipeline_items_run", table_name="discovery_pipeline_items"
    )
    op.drop_table("discovery_pipeline_items")
    op.drop_index(
        "uq_pipeline_runs_one_active_editorial_generation",
        table_name="pipeline_runs",
    )
    op.create_index(
        "uq_pipeline_runs_one_active_plant_profile",
        "pipeline_runs",
        [sa.text("(pipeline_type)")],
        unique=True,
        postgresql_where=sa.text(
            "pipeline_type = 'plant_profile_automation' AND status = 'running'"
        ),
    )
