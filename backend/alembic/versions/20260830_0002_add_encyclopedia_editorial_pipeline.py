# ruff: noqa: E501
"""Add encyclopedia editorial pipeline tables.

Revision ID: 20260830_0002
Revises: 20260829_0001
Create Date: 2026-08-30 17:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260830_0002"
down_revision: str | None = "20260829_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_identifier", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("original_language", sa.String(length=25), nullable=False),
        sa.Column("license_status", sa.String(length=255), nullable=False),
        sa.Column("supports", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("permitted_extract", sa.Text(), nullable=True),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_publication_date", sa.String(length=50), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_url", name="uq_source_records_canonical_url"),
        sa.UniqueConstraint(
            "source_id", "external_identifier", name="uq_source_records_source_external"
        ),
    )
    op.create_index("ix_source_records_source_id", "source_records", ["source_id"])

    op.create_table(
        "plant_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("accepted_scientific_name", sa.String(length=255), nullable=False),
        sa.Column("display_common_name", sa.String(length=255), nullable=False),
        sa.Column("family_name", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("introduction", sa.Text(), nullable=False),
        sa.Column("botanical_description", sa.Text(), nullable=False),
        sa.Column(
            "traditional_uses", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "parts_used", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("preparation", sa.Text(), nullable=False),
        sa.Column(
            "safety_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("evidence_notes", sa.Text(), nullable=False),
        sa.Column(
            "hero_image", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('collected','normalized','draft','needs_review','approved','rejected','held','published')",
            name="ck_plant_profiles_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_plant_profiles_slug"),
    )
    op.create_index("ix_plant_profiles_status", "plant_profiles", ["status"])
    op.create_index(
        "ix_plant_profiles_common_name", "plant_profiles", ["display_common_name"]
    )
    op.create_index(
        "ix_plant_profiles_scientific_name",
        "plant_profiles",
        ["accepted_scientific_name"],
    )

    op.create_table(
        "plant_profile_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plant_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("support_role", sa.String(length=100), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["plant_profile_id"], ["plant_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"], ["source_records.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plant_profile_id",
            "source_record_id",
            "support_role",
            name="uq_plant_profile_sources_role",
        ),
    )
    op.create_index(
        "ix_plant_profile_sources_plant", "plant_profile_sources", ["plant_profile_id"]
    )

    op.create_table(
        "editorial_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plant_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reviewer_name", sa.String(length=255), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column(
            "review_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('needs_review','approved','rejected','held')",
            name="ck_editorial_reviews_status",
        ),
        sa.ForeignKeyConstraint(
            ["plant_profile_id"], ["plant_profiles.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_editorial_reviews_status", "editorial_reviews", ["status"])

    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_type", sa.String(length=100), nullable=False),
        sa.Column("trigger", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_stage", sa.String(length=100), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('running','succeeded','failed','held','partial')",
            name="ck_pipeline_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_pipeline_runs_idempotency_key"),
    )
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])

    op.create_table(
        "pipeline_stage_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column(
            "input_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "output_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('pending','succeeded','failed','held','skipped')",
            name="ck_pipeline_stage_results_status",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pipeline_run_id", "name", name="uq_pipeline_stage_run_name"
        ),
    )
    op.create_index(
        "ix_pipeline_stage_results_run", "pipeline_stage_results", ["pipeline_run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_stage_results_run", table_name="pipeline_stage_results")
    op.drop_table("pipeline_stage_results")
    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
    op.drop_index("ix_editorial_reviews_status", table_name="editorial_reviews")
    op.drop_table("editorial_reviews")
    op.drop_index("ix_plant_profile_sources_plant", table_name="plant_profile_sources")
    op.drop_table("plant_profile_sources")
    op.drop_index("ix_plant_profiles_scientific_name", table_name="plant_profiles")
    op.drop_index("ix_plant_profiles_common_name", table_name="plant_profiles")
    op.drop_index("ix_plant_profiles_status", table_name="plant_profiles")
    op.drop_table("plant_profiles")
    op.drop_index("ix_source_records_source_id", table_name="source_records")
    op.drop_table("source_records")
