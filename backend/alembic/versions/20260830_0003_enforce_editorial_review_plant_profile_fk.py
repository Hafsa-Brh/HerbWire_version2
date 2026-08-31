# ruff: noqa: E501
"""Enforce editorial review plant profile integrity.

Revision ID: 20260830_0003
Revises: 20260830_0002
Create Date: 2026-08-30 18:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260830_0003"
down_revision: str | None = "20260830_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    null_review_count = bind.execute(
        sa.text("SELECT count(*) FROM editorial_reviews WHERE plant_profile_id IS NULL")
    ).scalar_one()
    if null_review_count:
        raise RuntimeError(
            "Cannot apply 20260830_0003: editorial_reviews.plant_profile_id contains "
            f"{null_review_count} NULL row(s). Resolve orphaned review rows before "
            "running this corrective upgrade."
        )

    op.drop_constraint(
        "editorial_reviews_plant_profile_id_fkey",
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


def downgrade() -> None:
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
        "editorial_reviews_plant_profile_id_fkey",
        "editorial_reviews",
        "plant_profiles",
        ["plant_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
