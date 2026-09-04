"""Curated Materials & Craft persistence."""

import uuid
from datetime import datetime, timezone

from backend.app.db.base import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MaterialStory(Base):
    __tablename__ = "material_stories"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    deck: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    material_labels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    geography_label: Mapped[str | None] = mapped_column(String(180))
    sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reading_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="published")
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hero_media: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    sources: Mapped[list["MaterialStorySource"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )
    __table_args__ = (
        CheckConstraint(
            "status in ('draft','published')", name="ck_material_stories_status"
        ),
        CheckConstraint(
            "content_version >= 1", name="ck_material_stories_content_version"
        ),
        CheckConstraint(
            "reading_time_minutes >= 1", name="ck_material_stories_reading_time"
        ),
        UniqueConstraint(
            "slug", "content_version", name="uq_material_stories_slug_version"
        ),
        Index(
            "ix_material_stories_public_order",
            "status",
            "featured",
            "published_at",
            "id",
        ),
        Index("ix_material_stories_category", "category"),
    )


class MaterialStorySource(Base):
    __tablename__ = "material_story_sources"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    material_story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("material_stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    support_role: Mapped[str] = mapped_column(String(100), nullable=False)
    supported_sections: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    story: Mapped[MaterialStory] = relationship(back_populates="sources")
    source_record = relationship("SourceRecord", back_populates="material_story_links")
    __table_args__ = (
        UniqueConstraint(
            "material_story_id",
            "source_record_id",
            "support_role",
            name="uq_material_story_sources_role",
        ),
        Index("ix_material_story_sources_story", "material_story_id"),
        Index("ix_material_story_sources_record", "source_record_id"),
    )
