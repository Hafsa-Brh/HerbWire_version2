"""Add the PubMed discovery review slice.

Revision ID: 20260902_0008
Revises: 20260901_0007
Create Date: 2026-09-02 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260902_0008"
down_revision: str | None = "20260901_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_records", sa.Column("doi", sa.String(255), nullable=True))
    op.add_column(
        "source_records",
        sa.Column(
            "authors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("source_records", sa.Column("journal", sa.String(500), nullable=True))
    op.create_unique_constraint("uq_source_records_doi", "source_records", ["doi"])
    op.create_unique_constraint(
        "uq_source_records_source_content_hash",
        "source_records",
        ["source_id", "content_hash"],
    )

    op.execute(
        """
        INSERT INTO sources (
            id, identifier, name, base_url, status, created_at, updated_at
        )
        VALUES (
            '00000000-0000-4000-8000-000000000008',
            'pubmed-eutils',
            'PubMed / NCBI E-utilities',
            'https://pubmed.ncbi.nlm.nih.gov/',
            'approved',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (identifier) DO NOTHING
        """
    )
    op.add_column(
        "pipeline_stage_results",
        sa.Column("input_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pipeline_stage_results",
        sa.Column("output_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "discovery_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("relevance_confidence", sa.Float(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "evidence_signals",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "detected_entities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "evidence_package",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('relevant','irrelevant','enriched','held')",
            name="ck_discovery_events_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["source_records.id"],
            name="fk_discovery_events_source_record",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_record_id", name="uq_discovery_events_source_record"
        ),
    )
    op.create_index("ix_discovery_events_status", "discovery_events", ["status"])
    op.create_index("ix_discovery_events_category", "discovery_events", ["category"])

    op.create_table(
        "discovery_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("standfirst", sa.Text(), nullable=False),
        sa.Column(
            "body_blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "limitations", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("safety_context", sa.Text(), nullable=False),
        sa.Column(
            "cannot_conclude", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "qa_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("content_checksum", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in "
            "('draft','needs_review','approved','rejected','held','published')",
            name="ck_discovery_articles_status",
        ),
        sa.CheckConstraint("version > 0", name="ck_discovery_articles_version"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["discovery_events.id"],
            name="fk_discovery_articles_event",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_checksum", name="uq_discovery_articles_checksum"),
        sa.UniqueConstraint("event_id", name="uq_discovery_articles_event"),
        sa.UniqueConstraint("slug", name="uq_discovery_articles_slug"),
    )
    op.create_index("ix_discovery_articles_status", "discovery_articles", ["status"])
    op.create_index(
        "ix_discovery_articles_created_at", "discovery_articles", ["created_at"]
    )

    op.create_table(
        "discovery_article_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "discovery_article_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("support_role", sa.String(100), nullable=False),
        sa.Column(
            "evidence_locations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["discovery_article_id"],
            ["discovery_articles.id"],
            name="fk_discovery_article_sources_article",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["source_records.id"],
            name="fk_discovery_article_sources_source_record",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "discovery_article_id",
            "source_record_id",
            "support_role",
            name="uq_discovery_article_sources_role",
        ),
    )
    op.create_index(
        "ix_discovery_article_sources_article",
        "discovery_article_sources",
        ["discovery_article_id"],
    )

    op.drop_constraint(
        "fk_editorial_reviews_plant_profile_id",
        "editorial_reviews",
        type_="foreignkey",
    )
    op.alter_column(
        "editorial_reviews",
        "plant_profile_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_editorial_reviews_plant_profile_id",
        "editorial_reviews",
        "plant_profiles",
        ["plant_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "editorial_reviews",
        sa.Column("discovery_article_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_editorial_reviews_discovery_article_id",
        "editorial_reviews",
        "discovery_articles",
        ["discovery_article_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_editorial_reviews_discovery_article",
        "editorial_reviews",
        ["discovery_article_id"],
    )
    op.create_check_constraint(
        "ck_editorial_reviews_exactly_one_content",
        "editorial_reviews",
        "(plant_profile_id IS NOT NULL AND discovery_article_id IS NULL) OR "
        "(plant_profile_id IS NULL AND discovery_article_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.execute("DELETE FROM editorial_reviews WHERE discovery_article_id IS NOT NULL")
    op.drop_constraint(
        "ck_editorial_reviews_exactly_one_content",
        "editorial_reviews",
        type_="check",
    )
    op.drop_constraint(
        "uq_editorial_reviews_discovery_article",
        "editorial_reviews",
        type_="unique",
    )
    op.drop_constraint(
        "fk_editorial_reviews_discovery_article_id",
        "editorial_reviews",
        type_="foreignkey",
    )
    op.drop_column("editorial_reviews", "discovery_article_id")
    op.drop_constraint(
        "fk_editorial_reviews_plant_profile_id",
        "editorial_reviews",
        type_="foreignkey",
    )
    op.alter_column(
        "editorial_reviews",
        "plant_profile_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_editorial_reviews_plant_profile_id",
        "editorial_reviews",
        "plant_profiles",
        ["plant_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_index(
        "ix_discovery_article_sources_article",
        table_name="discovery_article_sources",
    )
    op.drop_table("discovery_article_sources")
    op.drop_index("ix_discovery_articles_created_at", table_name="discovery_articles")
    op.drop_index("ix_discovery_articles_status", table_name="discovery_articles")
    op.drop_table("discovery_articles")
    op.drop_index("ix_discovery_events_category", table_name="discovery_events")
    op.drop_index("ix_discovery_events_status", table_name="discovery_events")
    op.drop_table("discovery_events")

    op.execute(
        """
        DELETE FROM source_records
        WHERE source_id IN (
            SELECT id FROM sources WHERE identifier = 'pubmed-eutils'
        )
        """
    )
    op.execute("DELETE FROM sources WHERE identifier = 'pubmed-eutils'")
    op.drop_column("pipeline_stage_results", "output_count")
    op.drop_column("pipeline_stage_results", "input_count")
    op.drop_constraint(
        "uq_source_records_source_content_hash", "source_records", type_="unique"
    )
    op.drop_constraint("uq_source_records_doi", "source_records", type_="unique")
    op.drop_column("source_records", "journal")
    op.drop_column("source_records", "authors")
    op.drop_column("source_records", "doi")
