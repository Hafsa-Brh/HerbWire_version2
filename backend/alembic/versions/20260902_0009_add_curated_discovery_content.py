"""Add curated discovery article content.

Revision ID: 20260902_0009
Revises: 20260902_0008
Create Date: 2026-09-02 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260902_0009"
down_revision: str | None = "20260902_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discovery_articles",
        sa.Column(
            "content_origin", sa.String(50), nullable=False, server_default="automated"
        ),
    )
    op.add_column(
        "discovery_articles", sa.Column("article_type", sa.String(100), nullable=True)
    )
    op.add_column(
        "discovery_articles", sa.Column("research_date", sa.String(50), nullable=True)
    )
    for name in (
        "research_question",
        "research_context",
        "study_design",
        "evidence_base",
        "intervention",
        "comparator",
        "evidence_strength_rationale",
        "why_matters",
        "practical_interpretation",
    ):
        op.add_column("discovery_articles", sa.Column(name, sa.Text(), nullable=True))
    op.add_column(
        "discovery_articles",
        sa.Column(
            "main_findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "discovery_articles",
        sa.Column("evidence_strength", sa.String(50), nullable=True),
    )
    for name, default in (
        ("section_sources", "'{}'::jsonb"),
        ("hero_image", "'{}'::jsonb"),
        ("geography", "'[]'::jsonb"),
    ):
        op.add_column(
            "discovery_articles",
            sa.Column(
                name,
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text(default),
            ),
        )
    op.create_check_constraint(
        "ck_discovery_articles_content_origin",
        "discovery_articles",
        "content_origin in ('automated','curated','synthetic')",
    )
    op.create_table(
        "discovery_article_plants",
        sa.Column(
            "discovery_article_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("plant_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["discovery_article_id"],
            ["discovery_articles.id"],
            name="fk_discovery_article_plants_article",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plant_profile_id"],
            ["plant_profiles.id"],
            name="fk_discovery_article_plants_profile",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("discovery_article_id", "plant_profile_id"),
    )
    op.create_index(
        "ix_discovery_article_plants_profile",
        "discovery_article_plants",
        ["plant_profile_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_discovery_article_plants_profile", table_name="discovery_article_plants"
    )
    op.drop_table("discovery_article_plants")
    op.drop_constraint(
        "ck_discovery_articles_content_origin", "discovery_articles", type_="check"
    )
    for name in (
        "geography",
        "hero_image",
        "section_sources",
        "practical_interpretation",
        "why_matters",
        "evidence_strength_rationale",
        "evidence_strength",
        "main_findings",
        "comparator",
        "intervention",
        "evidence_base",
        "study_design",
        "research_context",
        "research_question",
        "research_date",
        "article_type",
        "content_origin",
    ):
        op.drop_column("discovery_articles", name)
