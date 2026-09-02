# ruff: noqa: E501
import uuid
from datetime import datetime, timezone

from backend.app.db.base import Base
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

PLANT_STATUSES = (
    "collected",
    "normalized",
    "draft",
    "needs_review",
    "approved",
    "rejected",
    "held",
    "published",
)

REVIEW_STATUSES = ("needs_review", "approved", "rejected", "held")
REVISION_STATUSES = ("needs_review", "approved", "held", "promoted", "superseded")
PIPELINE_STATUSES = ("running", "succeeded", "failed", "held", "partial")
STAGE_STATUSES = ("pending", "succeeded", "failed", "held", "skipped")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_language: Mapped[str] = mapped_column(
        String(25), nullable=False, default="en"
    )
    license_status: Mapped[str] = mapped_column(String(255), nullable=False)
    supports: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    permitted_extract: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_publication_date: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    journal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    plant_links: Mapped[list["PlantProfileSource"]] = relationship(
        back_populates="source_record"
    )
    discovery_events: Mapped[list["DiscoveryEvent"]] = relationship(
        back_populates="source_record"
    )
    discovery_article_links: Mapped[list["DiscoveryArticleSource"]] = relationship(
        back_populates="source_record"
    )

    __table_args__ = (
        UniqueConstraint(
            "source_id", "external_identifier", name="uq_source_records_source_external"
        ),
        UniqueConstraint("canonical_url", name="uq_source_records_canonical_url"),
        UniqueConstraint("doi", name="uq_source_records_doi"),
        UniqueConstraint(
            "source_id", "content_hash", name="uq_source_records_source_content_hash"
        ),
        Index("ix_source_records_source_id", "source_id"),
    )


class DiscoveryEvent(Base):
    __tablename__ = "discovery_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    relevance_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_signals: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    detected_entities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_package: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    source_record: Mapped[SourceRecord] = relationship(
        back_populates="discovery_events"
    )
    article: Mapped["DiscoveryArticle | None"] = relationship(
        back_populates="event", uselist=False
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('relevant','irrelevant','enriched','held')",
            name="ck_discovery_events_status",
        ),
        Index("ix_discovery_events_status", "status"),
        Index("ix_discovery_events_category", "category"),
    )


class DiscoveryArticle(Base):
    __tablename__ = "discovery_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_events.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    standfirst: Mapped[str] = mapped_column(Text, nullable=False)
    body_blocks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    limitations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    safety_context: Mapped[str] = mapped_column(Text, nullable=False)
    cannot_conclude: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    qa_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    content_checksum: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    event: Mapped[DiscoveryEvent] = relationship(back_populates="article")
    sources: Mapped[list["DiscoveryArticleSource"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["EditorialReview"]] = relationship(
        back_populates="discovery_article"
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('draft','needs_review','approved','rejected','held','published')",
            name="ck_discovery_articles_status",
        ),
        CheckConstraint("version > 0", name="ck_discovery_articles_version"),
        Index("ix_discovery_articles_status", "status"),
        Index("ix_discovery_articles_created_at", "created_at"),
    )


class DiscoveryArticleSource(Base):
    __tablename__ = "discovery_article_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discovery_article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    support_role: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_locations: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    article: Mapped[DiscoveryArticle] = relationship(back_populates="sources")
    source_record: Mapped[SourceRecord] = relationship(
        back_populates="discovery_article_links"
    )

    __table_args__ = (
        UniqueConstraint(
            "discovery_article_id",
            "source_record_id",
            "support_role",
            name="uq_discovery_article_sources_role",
        ),
        Index("ix_discovery_article_sources_article", "discovery_article_id"),
    )


class PlantProfile(Base):
    __tablename__ = "plant_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    accepted_scientific_name: Mapped[str] = mapped_column(String(255), nullable=False)
    botanical_author: Mapped[str] = mapped_column(
        String(255), nullable=False, default=""
    )
    taxon_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, default=""
    )
    known_synonyms: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    display_common_name: Mapped[str] = mapped_column(String(255), nullable=False)
    family_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    diversity_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    introduction: Mapped[str] = mapped_column(Text, nullable=False)
    botanical_description: Mapped[str] = mapped_column(Text, nullable=False)
    traditional_uses: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    parts_used: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    distribution: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    distribution_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    growth_form: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    biome: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    preparation: Mapped[str] = mapped_column(Text, nullable=False)
    safety_notes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_notes: Mapped[str] = mapped_column(Text, nullable=False)
    article_details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    readiness_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="legacy"
    )
    readiness_reason: Mapped[str | None] = mapped_column(Text)
    hero_image: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    sources: Mapped[list["PlantProfileSource"]] = relationship(
        back_populates="plant_profile", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["EditorialReview"]] = relationship(
        back_populates="plant_profile"
    )
    revisions: Mapped[list["PlantProfileRevision"]] = relationship(
        back_populates="plant_profile"
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('collected','normalized','draft','needs_review','approved','rejected','held','published')",
            name="ck_plant_profiles_status",
        ),
        CheckConstraint(
            "readiness_status in ('legacy','ready_for_review','held')",
            name="ck_plant_profiles_readiness_status",
        ),
        Index("ix_plant_profiles_status", "status"),
        Index("ix_plant_profiles_common_name", "display_common_name"),
        Index("ix_plant_profiles_scientific_name", "accepted_scientific_name"),
    )


class PlantProfileRevision(Base):
    __tablename__ = "plant_profile_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plant_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plant_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    content_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="needs_review"
    )
    reviewer_name: Mapped[str | None] = mapped_column(String(255))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plant_profile: Mapped[PlantProfile] = relationship(back_populates="revisions")

    __table_args__ = (
        CheckConstraint("version > 0", name="ck_plant_profile_revisions_version"),
        CheckConstraint(
            "status in ('needs_review','approved','held','promoted','superseded')",
            name="ck_plant_profile_revisions_status",
        ),
        UniqueConstraint(
            "plant_profile_id", "version", name="uq_plant_profile_revisions_version"
        ),
        UniqueConstraint(
            "plant_profile_id",
            "content_checksum",
            name="uq_plant_profile_revisions_checksum",
        ),
        Index("ix_plant_profile_revisions_profile", "plant_profile_id"),
        Index("ix_plant_profile_revisions_status", "status"),
    )


class PlantProfileSource(Base):
    __tablename__ = "plant_profile_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plant_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plant_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    support_role: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    plant_profile: Mapped[PlantProfile] = relationship(back_populates="sources")
    source_record: Mapped[SourceRecord] = relationship(back_populates="plant_links")

    __table_args__ = (
        UniqueConstraint(
            "plant_profile_id",
            "source_record_id",
            "support_role",
            name="uq_plant_profile_sources_role",
        ),
        Index("ix_plant_profile_sources_plant", "plant_profile_id"),
    )


class EditorialReview(Base):
    __tablename__ = "editorial_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plant_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plant_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    discovery_article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_articles.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="needs_review"
    )
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plant_profile: Mapped[PlantProfile | None] = relationship(back_populates="reviews")
    discovery_article: Mapped[DiscoveryArticle | None] = relationship(
        back_populates="reviews"
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('needs_review','approved','rejected','held')",
            name="ck_editorial_reviews_status",
        ),
        CheckConstraint(
            "(plant_profile_id IS NOT NULL AND discovery_article_id IS NULL) OR "
            "(plant_profile_id IS NULL AND discovery_article_id IS NOT NULL)",
            name="ck_editorial_reviews_exactly_one_content",
        ),
        Index("ix_editorial_reviews_status", "status"),
    )


class NewsletterSubscription(Base):
    __tablename__ = "newsletter_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (Index("ix_newsletter_subscriptions_email", "email"),)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_type: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    stages: Mapped[list["PipelineStageResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('running','succeeded','failed','held','partial')",
            name="ck_pipeline_runs_status",
        ),
        Index("ix_pipeline_runs_status", "status"),
    )


class PipelineStageResult(Base):
    __tablename__ = "pipeline_stage_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    attempt: Mapped[int] = mapped_column(nullable=False, default=1)
    duration_ms: Mapped[int] = mapped_column(nullable=False, default=0)
    input_count: Mapped[int] = mapped_column(nullable=False, default=0)
    output_count: Mapped[int] = mapped_column(nullable=False, default=0)
    input_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    output_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    run: Mapped[PipelineRun] = relationship(back_populates="stages")

    __table_args__ = (
        CheckConstraint(
            "status in ('pending','succeeded','failed','held','skipped')",
            name="ck_pipeline_stage_results_status",
        ),
        UniqueConstraint("pipeline_run_id", "name", name="uq_pipeline_stage_run_name"),
        Index("ix_pipeline_stage_results_run", "pipeline_run_id"),
    )
