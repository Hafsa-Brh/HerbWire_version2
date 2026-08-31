"""add reviewed plant profile revisions

Revision ID: 20260901_0006
Revises: 20260831_0005
Create Date: 2026-09-01 00:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260901_0006"
down_revision: str | None = "20260831_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plant_profile_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plant_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "content_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reviewer_name", sa.String(length=255), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('needs_review','approved','held','promoted','superseded')",
            name="ck_plant_profile_revisions_status",
        ),
        sa.CheckConstraint("version > 0", name="ck_plant_profile_revisions_version"),
        sa.ForeignKeyConstraint(
            ["plant_profile_id"],
            ["plant_profiles.id"],
            name="fk_plant_profile_revisions_profile",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plant_profile_id",
            "content_checksum",
            name="uq_plant_profile_revisions_checksum",
        ),
        sa.UniqueConstraint(
            "plant_profile_id",
            "version",
            name="uq_plant_profile_revisions_version",
        ),
    )
    op.create_index(
        "ix_plant_profile_revisions_profile",
        "plant_profile_revisions",
        ["plant_profile_id"],
    )
    op.create_index(
        "ix_plant_profile_revisions_status",
        "plant_profile_revisions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_plant_profile_revisions_status",
        table_name="plant_profile_revisions",
    )
    op.drop_index(
        "ix_plant_profile_revisions_profile",
        table_name="plant_profile_revisions",
    )
    op.drop_table("plant_profile_revisions")
