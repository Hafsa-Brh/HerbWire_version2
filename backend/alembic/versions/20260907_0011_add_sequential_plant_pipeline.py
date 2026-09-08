"""Add durable sequential Plant pipeline state.

Revision ID: 20260907_0011
Revises: 20260903_0010
Create Date: 2026-09-07 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260907_0011"
down_revision: str | None = "20260903_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
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

    op.drop_constraint(
        "ck_pipeline_stage_results_status", "pipeline_stage_results", type_="check"
    )
    op.drop_constraint(
        "uq_pipeline_stage_run_name", "pipeline_stage_results", type_="unique"
    )
    op.add_column(
        "pipeline_stage_results",
        sa.Column("candidate_position", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pipeline_stage_results",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pipeline_stage_results",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_pipeline_stage_results_status",
        "pipeline_stage_results",
        "status in ('pending','running','succeeded','failed','held','skipped')",
    )
    op.create_unique_constraint(
        "uq_pipeline_stage_run_name_candidate",
        "pipeline_stage_results",
        ["pipeline_run_id", "name", "candidate_position"],
    )

    op.create_table(
        "plant_pipeline_items",
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
        sa.Column("plant_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('pending','running','succeeded','failed','held')",
            name="ck_plant_pipeline_items_status",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["plant_profile_id"], ["plant_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["review_id"], ["editorial_reviews.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_key", name="uq_plant_pipeline_candidate_key"),
        sa.UniqueConstraint(
            "pipeline_run_id", "position", name="uq_plant_pipeline_items_position"
        ),
        sa.UniqueConstraint("plant_profile_id", name="uq_plant_pipeline_items_profile"),
        sa.UniqueConstraint("review_id", name="uq_plant_pipeline_items_review"),
    )
    op.create_index(
        "ix_plant_pipeline_items_run", "plant_pipeline_items", ["pipeline_run_id"]
    )
    op.create_index(
        "ix_plant_pipeline_items_status", "plant_pipeline_items", ["status"]
    )

    op.create_index(
        "uq_plant_profiles_taxon_identifier_nonempty",
        "plant_profiles",
        [sa.text("lower(taxon_identifier)")],
        unique=True,
        postgresql_where=sa.text("btrim(taxon_identifier) <> ''"),
    )
    op.create_index(
        "uq_plant_profiles_scientific_name_normalized",
        "plant_profiles",
        [
            sa.text(
                "lower(regexp_replace(accepted_scientific_name, "
                "'[[:space:][:punct:]]', '', 'g'))"
            )
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_plant_profiles_scientific_name_normalized", table_name="plant_profiles"
    )
    op.drop_index(
        "uq_plant_profiles_taxon_identifier_nonempty", table_name="plant_profiles"
    )
    op.drop_index("ix_plant_pipeline_items_status", table_name="plant_pipeline_items")
    op.drop_index("ix_plant_pipeline_items_run", table_name="plant_pipeline_items")
    op.drop_table("plant_pipeline_items")

    op.drop_constraint(
        "uq_pipeline_stage_run_name_candidate",
        "pipeline_stage_results",
        type_="unique",
    )
    op.drop_constraint(
        "ck_pipeline_stage_results_status",
        "pipeline_stage_results",
        type_="check",
    )
    op.drop_column("pipeline_stage_results", "completed_at")
    op.drop_column("pipeline_stage_results", "started_at")
    op.drop_column("pipeline_stage_results", "candidate_position")
    op.create_check_constraint(
        "ck_pipeline_stage_results_status",
        "pipeline_stage_results",
        "status in ('pending','succeeded','failed','held','skipped')",
    )
    op.create_unique_constraint(
        "uq_pipeline_stage_run_name",
        "pipeline_stage_results",
        ["pipeline_run_id", "name"],
    )

    op.drop_index(
        "uq_pipeline_runs_one_active_plant_profile", table_name="pipeline_runs"
    )
    op.drop_column("pipeline_runs", "lease_expires_at")
    op.drop_column("pipeline_runs", "heartbeat_at")
