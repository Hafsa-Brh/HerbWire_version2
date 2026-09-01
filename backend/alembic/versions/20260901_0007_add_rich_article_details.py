"""add rich article details

Revision ID: 20260901_0007
Revises: 20260901_0006
Create Date: 2026-09-01 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260901_0007"
down_revision: str | None = "20260901_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plant_profiles",
        sa.Column(
            "article_details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("plant_profiles", "article_details")
