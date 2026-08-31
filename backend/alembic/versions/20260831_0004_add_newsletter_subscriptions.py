"""add newsletter subscriptions

Revision ID: 20260831_0004
Revises: 20260830_0003
Create Date: 2026-08-31 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260831_0004"
down_revision: str | None = "20260830_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "newsletter_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_newsletter_subscriptions_email"),
    )
    op.create_index(
        "ix_newsletter_subscriptions_email",
        "newsletter_subscriptions",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_newsletter_subscriptions_email", table_name="newsletter_subscriptions"
    )
    op.drop_table("newsletter_subscriptions")
