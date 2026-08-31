"""add curated corpus profile metadata

Revision ID: 20260831_0005
Revises: 20260831_0004
Create Date: 2026-08-31 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260831_0005"
down_revision: str | None = "20260831_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plant_profiles",
        sa.Column(
            "botanical_author", sa.String(length=255), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "plant_profiles",
        sa.Column(
            "taxon_identifier", sa.String(length=255), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "plant_profiles",
        sa.Column(
            "known_synonyms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "plant_profiles",
        sa.Column(
            "diversity_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "plant_profiles",
        sa.Column("distribution_summary", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "plant_profiles",
        sa.Column(
            "growth_form", sa.String(length=255), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "plant_profiles",
        sa.Column("biome", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "plant_profiles",
        sa.Column(
            "readiness_status",
            sa.String(length=50),
            nullable=False,
            server_default="legacy",
        ),
    )
    op.add_column(
        "plant_profiles", sa.Column("readiness_reason", sa.Text(), nullable=True)
    )
    op.create_check_constraint(
        "ck_plant_profiles_readiness_status",
        "plant_profiles",
        "readiness_status in ('legacy','ready_for_review','held')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_plant_profiles_readiness_status", "plant_profiles", type_="check"
    )
    for column in (
        "readiness_reason",
        "readiness_status",
        "biome",
        "growth_form",
        "distribution_summary",
        "diversity_tags",
        "known_synonyms",
        "taxon_identifier",
        "botanical_author",
    ):
        op.drop_column("plant_profiles", column)
