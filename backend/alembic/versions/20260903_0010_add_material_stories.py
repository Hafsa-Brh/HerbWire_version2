"""Add curated material stories.

Revision ID: 20260903_0010
Revises: 20260902_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260903_0010"
down_revision: str | None = "20260902_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "material_stories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("content_version", sa.Integer(), nullable=False),
        sa.Column("content_checksum", sa.String(64), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("deck", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("material_labels", postgresql.JSONB(), nullable=False),
        sa.Column("geography_label", sa.String(180), nullable=True),
        sa.Column("sections", postgresql.JSONB(), nullable=False),
        sa.Column("reading_time_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("hero_media", postgresql.JSONB(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "content_version >= 1", name="ck_material_stories_content_version"
        ),
        sa.CheckConstraint(
            "reading_time_minutes >= 1", name="ck_material_stories_reading_time"
        ),
        sa.CheckConstraint(
            "status in ('draft','published')", name="ck_material_stories_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_material_stories_slug"),
        sa.UniqueConstraint(
            "slug", "content_version", name="uq_material_stories_slug_version"
        ),
    )
    op.create_index(
        "ix_material_stories_public_order",
        "material_stories",
        ["status", "featured", "published_at", "id"],
    )
    op.create_index("ix_material_stories_category", "material_stories", ["category"])
    op.create_table(
        "material_story_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("support_role", sa.String(100), nullable=False),
        sa.Column("supported_sections", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["material_story_id"], ["material_stories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"], ["source_records.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_story_id",
            "source_record_id",
            "support_role",
            name="uq_material_story_sources_role",
        ),
    )
    op.create_index(
        "ix_material_story_sources_story",
        "material_story_sources",
        ["material_story_id"],
    )
    op.create_index(
        "ix_material_story_sources_record",
        "material_story_sources",
        ["source_record_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_material_story_sources_record", table_name="material_story_sources"
    )
    op.drop_index(
        "ix_material_story_sources_story", table_name="material_story_sources"
    )
    op.drop_table("material_story_sources")
    op.drop_index("ix_material_stories_category", table_name="material_stories")
    op.drop_index("ix_material_stories_public_order", table_name="material_stories")
    op.drop_table("material_stories")
