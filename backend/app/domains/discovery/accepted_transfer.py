from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from backend.app.domains.discovery.corpus import (
    CuratedDiscovery,
    CuratedDiscoveryCorpus,
    load_curated_discovery_corpus,
    load_final_discovery_corpus,
    load_new_plant_discovery_corpus,
)
from backend.app.domains.discovery.curated_import import import_curated_discoveries
from backend.app.domains.discovery.service import publish_discovery_article
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryArticleSource,
    EditorialReview,
    PlantProfile,
    SourceRecord,
)
from backend.app.models.source import Source
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

MANIFEST_PATH = Path(__file__).with_name("owner_accepted_publication_manifest.json")
EXPECTED_DISCOVERY_COUNT = 30
TRANSFER_REVIEWER_NAME = "Local editor"


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _checksum(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def source_identity_checksum(article: CuratedDiscovery) -> str:
    return _checksum(
        sorted(
            (
                {
                    "source_id": item.source_id,
                    "provider": item.provider,
                    "external_identifier": item.stable_identifier,
                    "pmid": item.pmid,
                    "doi": item.doi,
                    "support_role": item.support_role,
                    "canonical_url": str(item.canonical_url),
                }
                for item in article.sources
            ),
            key=lambda item: item["source_id"],
        )
    )


def geography_checksum(article: CuratedDiscovery) -> str:
    geography = [item.model_dump(mode="json") for item in article.geography]
    return _persisted_geography_checksum(geography, article)


def _persisted_geography_checksum(
    geography: list[dict], article: CuratedDiscovery
) -> str:
    normalized = [dict(item) for item in geography]
    if article.plant_slug is not None:
        for item in normalized:
            item.pop("geography_kind", None)
            item.pop("iso_country_codes", None)
    return _checksum(normalized)


class AcceptedDiscoveryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    content_version: int = Field(ge=1)
    content_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    primary_pmid: str = Field(pattern=r"^\d+$")
    primary_doi: str
    source_identity_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    geography_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    article_state: Literal["published"]
    review_state: Literal["approved"]
    reviewed_at: datetime
    decided_at: datetime
    published_at: datetime

    @model_validator(mode="after")
    def validate_timestamps(self):
        if any(
            value.tzinfo is None
            for value in (self.reviewed_at, self.decided_at, self.published_at)
        ):
            raise ValueError("accepted timestamps must be timezone-aware")
        return self


class AcceptedDiscoveryManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal[1]
    accepted_state_id: Literal["herbwire-owner-review-20260903"]
    reviewer_identity: Literal["single-owner-editorial-desk"]
    corpus_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    decisions: list[AcceptedDiscoveryDecision]
    manifest_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")

    def calculated_checksum(self) -> str:
        return _checksum(self.model_dump(mode="json", exclude={"manifest_checksum"}))

    @model_validator(mode="after")
    def validate_manifest(self):
        if len(self.decisions) != EXPECTED_DISCOVERY_COUNT:
            raise ValueError("publication manifest must contain exactly 30 decisions")
        for attribute in ("slug", "primary_pmid", "primary_doi"):
            values = [getattr(item, attribute) for item in self.decisions]
            if len(values) != len(set(values)):
                raise ValueError(f"publication manifest has duplicate {attribute}")
        if self.manifest_checksum != self.calculated_checksum():
            raise ValueError("publication manifest checksum mismatch")
        return self


@dataclass(frozen=True)
class AcceptedTransferSummary:
    created: int
    transferred: int
    unchanged: int
    verified: int
    dry_run: bool
    corpus_checksum: str
    manifest_checksum: str


def load_accepted_manifest(
    path: Path = MANIFEST_PATH,
) -> AcceptedDiscoveryManifest:
    return AcceptedDiscoveryManifest.model_validate_json(path.read_text("utf-8"))


def load_all_curated_discovery_corpora() -> tuple[CuratedDiscoveryCorpus, ...]:
    return (
        load_curated_discovery_corpus(),
        load_new_plant_discovery_corpus(),
        load_final_discovery_corpus(),
    )


def _corpus_articles(
    corpora: tuple[CuratedDiscoveryCorpus, ...],
) -> dict[str, CuratedDiscovery]:
    articles = [article for corpus in corpora for article in corpus.articles]
    if len(articles) != EXPECTED_DISCOVERY_COUNT:
        raise ValueError("combined curated corpus must contain exactly 30 articles")
    by_slug = {article.slug: article for article in articles}
    if len(by_slug) != EXPECTED_DISCOVERY_COUNT:
        raise ValueError("combined curated corpus contains duplicate slugs")
    for attribute in ("pmid", "doi"):
        values = [
            getattr(
                next(
                    source
                    for source in article.sources
                    if source.support_role == "primary_evidence"
                ),
                attribute,
            )
            for article in articles
        ]
        if any(value is None for value in values) or len(values) != len(set(values)):
            raise ValueError(f"combined curated corpus requires 30 unique {attribute}s")
    return by_slug


def _corpus_checksum(articles: dict[str, CuratedDiscovery]) -> str:
    return _checksum(
        [
            {
                "slug": article.slug,
                "content_version": article.content_version,
                "content_checksum": article.content_checksum,
            }
            for article in sorted(articles.values(), key=lambda item: item.slug)
        ]
    )


def _validate_manifest_against_corpus(
    manifest: AcceptedDiscoveryManifest,
    articles: dict[str, CuratedDiscovery],
) -> dict[str, AcceptedDiscoveryDecision]:
    checksum = _corpus_checksum(articles)
    if manifest.corpus_checksum != checksum:
        raise ValueError("accepted manifest corpus checksum differs")
    decisions = {item.slug: item for item in manifest.decisions}
    if decisions.keys() != articles.keys():
        raise ValueError("accepted manifest and curated corpus slugs differ")
    for slug, article in articles.items():
        decision = decisions[slug]
        primary = next(
            item for item in article.sources if item.support_role == "primary_evidence"
        )
        expected = (
            article.content_version,
            article.content_checksum,
            primary.pmid,
            primary.doi,
            source_identity_checksum(article),
            geography_checksum(article),
        )
        actual = (
            decision.content_version,
            decision.content_checksum,
            decision.primary_pmid,
            decision.primary_doi,
            decision.source_identity_checksum,
            decision.geography_checksum_sha256,
        )
        if actual != expected:
            raise ValueError(f"accepted identity differs for {slug}")
    return decisions


def _validate_target_dependencies(
    session: Session,
    articles: dict[str, CuratedDiscovery],
    decisions: dict[str, AcceptedDiscoveryDecision],
) -> None:
    providers = {
        source.provider for article in articles.values() for source in article.sources
    }
    available = set(
        session.scalars(
            select(Source.identifier).where(Source.identifier.in_(providers))
        )
    )
    if available != providers:
        raise ValueError("required Discovery source providers are unavailable")
    plant_slugs = {
        article.plant_slug for article in articles.values() if article.plant_slug
    }
    profiles = {
        profile.slug: profile
        for profile in session.scalars(
            select(PlantProfile).where(PlantProfile.slug.in_(plant_slugs))
        )
    }
    if profiles.keys() != plant_slugs or any(
        profile.status != "published" for profile in profiles.values()
    ):
        raise ValueError("required published Plant Profiles are unavailable")

    for article in articles.values():
        media = (
            article.hero_image.model_dump(mode="json")
            if article.hero_image is not None
            else profiles[article.plant_slug].hero_image
        )
        if (
            media.get("checksum_sha256")
            != decisions[article.slug].media_checksum_sha256
            or not media.get("alt_text")
            or not media.get("license")
        ):
            raise ValueError(f"licensed media identity differs for {article.slug}")
        relative_path = str(media.get("local_path", "")).removeprefix("/")
        repository_root = Path(__file__).resolve().parents[4]
        media_paths = (
            repository_root / "frontend" / "public" / relative_path,
            repository_root / "frontend" / "dist" / relative_path,
        )
        media_path = next((path for path in media_paths if path.is_file()), None)
        if media_path is None:
            raise ValueError(f"licensed media file is missing for {article.slug}")
        if (
            hashlib.sha256(media_path.read_bytes()).hexdigest()
            != media["checksum_sha256"]
        ):
            raise ValueError(f"licensed media file differs for {article.slug}")
        for source in article.sources:
            registry = session.scalar(
                select(Source).where(Source.identifier == source.provider)
            )
            existing = session.scalar(
                select(SourceRecord).where(
                    SourceRecord.source_id == registry.id,
                    SourceRecord.external_identifier == source.stable_identifier,
                )
            )
            if existing and (
                existing.canonical_url != str(source.canonical_url)
                or existing.doi != source.doi
                or existing.title != source.title
            ):
                raise ValueError(
                    f"existing source metadata conflicts for {source.source_id}"
                )


def _load_articles(session: Session) -> list[DiscoveryArticle]:
    return list(
        session.scalars(
            select(DiscoveryArticle).options(
                selectinload(DiscoveryArticle.reviews),
                selectinload(DiscoveryArticle.sources).selectinload(
                    DiscoveryArticleSource.source_record
                ),
                selectinload(DiscoveryArticle.plant_links),
                selectinload(DiscoveryArticle.event),
            )
        ).all()
    )


def _source_identifier(session: Session, source_id) -> str:
    identifier = session.scalar(select(Source.identifier).where(Source.id == source_id))
    if identifier is None:
        raise ValueError("persisted Discovery source registry is unavailable")
    return identifier


def _validate_persisted_identity(
    session: Session,
    article: DiscoveryArticle,
    corpus_article: CuratedDiscovery,
    decision: AcceptedDiscoveryDecision,
    corpus_batch_id: str,
) -> None:
    if (
        article.version != decision.content_version
        or article.content_checksum != decision.content_checksum
        or article.content_origin != "curated"
        or article.hero_image.get("checksum_sha256") != decision.media_checksum_sha256
        or _persisted_geography_checksum(article.geography, corpus_article)
        != decision.geography_checksum_sha256
        or not article.qa_payload.get("passed")
    ):
        raise ValueError(f"persisted Discovery identity differs for {article.slug}")
    persisted_sources = sorted(
        (
            {
                "provider_identity": (
                    f"{_source_identifier(session, link.source_record.source_id)}:"
                    f"{link.source_record.external_identifier}"
                ),
                "support_role": link.support_role,
            }
            for link in article.sources
        ),
        key=lambda item: item["provider_identity"],
    )
    expected_sources = sorted(
        (
            {
                "provider_identity": f"{item.provider}:{item.stable_identifier}",
                "support_role": item.support_role,
            }
            for item in corpus_article.sources
        ),
        key=lambda item: item["provider_identity"],
    )
    if persisted_sources != expected_sources:
        raise ValueError(f"persisted source relationships differ for {article.slug}")
    expected_plant_links = int(corpus_article.plant_slug is not None)
    if len(article.plant_links) != expected_plant_links:
        raise ValueError(f"persisted Plant relationship differs for {article.slug}")
    if len(article.reviews) != 1:
        raise ValueError(f"persisted review identity differs for {article.slug}")
    review_payload = article.reviews[0].review_payload
    expected_review_payload = {
        "origin": "curated",
        "version": corpus_article.content_version,
        "content_checksum": corpus_article.content_checksum,
        "source_ids": [item.source_id for item in corpus_article.sources],
    }
    persisted_batch_id = review_payload.get("batch_id")
    payload_without_batch = {
        key: value for key, value in review_payload.items() if key != "batch_id"
    }
    if payload_without_batch != expected_review_payload or persisted_batch_id not in {
        None,
        corpus_batch_id,
    }:
        raise ValueError(f"persisted review payload differs for {article.slug}")


def _state_kind(
    article: DiscoveryArticle, decision: AcceptedDiscoveryDecision
) -> Literal["pending", "unchanged"]:
    review = article.reviews[0]
    if (
        article.status == "needs_review"
        and review.status == "needs_review"
        and article.reviewed_at is None
        and article.published_at is None
        and review.decided_at is None
    ):
        return "pending"
    if (
        article.status == decision.article_state
        and review.status == decision.review_state
        and article.reviewed_at == decision.reviewed_at
        and article.published_at == decision.published_at
        and review.decided_at == decision.decided_at
    ):
        return "unchanged"
    raise ValueError(f"existing editorial state conflicts for {article.slug}")


def transfer_owner_accepted_discoveries(
    session: Session,
    *,
    dry_run: bool = False,
    manifest: AcceptedDiscoveryManifest | None = None,
    corpora: tuple[CuratedDiscoveryCorpus, ...] | None = None,
) -> AcceptedTransferSummary:
    manifest = manifest or load_accepted_manifest()
    corpora = corpora or load_all_curated_discovery_corpora()
    corpus_articles = _corpus_articles(corpora)
    corpus_batches = {
        article.slug: corpus.batch_id
        for corpus in corpora
        for article in corpus.articles
    }
    decisions = _validate_manifest_against_corpus(manifest, corpus_articles)
    _validate_target_dependencies(session, corpus_articles, decisions)

    existing = _load_articles(session)
    unknown = sorted({article.slug for article in existing} - corpus_articles.keys())
    if unknown:
        raise ValueError("target contains unknown Discovery records")
    existing_by_slug = {article.slug: article for article in existing}
    unchanged = pending = 0
    for slug, article in existing_by_slug.items():
        _validate_persisted_identity(
            session,
            article,
            corpus_articles[slug],
            decisions[slug],
            corpus_batches[slug],
        )
        state = _state_kind(article, decisions[slug])
        unchanged += int(state == "unchanged")
        pending += int(state == "pending")
    missing = EXPECTED_DISCOVERY_COUNT - len(existing_by_slug)

    if dry_run:
        return AcceptedTransferSummary(
            created=missing,
            transferred=missing + pending,
            unchanged=unchanged,
            verified=EXPECTED_DISCOVERY_COUNT,
            dry_run=True,
            corpus_checksum=manifest.corpus_checksum,
            manifest_checksum=manifest.manifest_checksum,
        )

    try:
        created = 0
        for corpus in corpora:
            created += import_curated_discoveries(session, corpus, commit=False).created
        persisted = _load_articles(session)
        if len(persisted) != EXPECTED_DISCOVERY_COUNT:
            raise ValueError("target does not contain exactly 30 Discoveries")
        transferred = 0
        for article in persisted:
            decision = decisions[article.slug]
            _validate_persisted_identity(
                session,
                article,
                corpus_articles[article.slug],
                decision,
                corpus_batches[article.slug],
            )
            state = _state_kind(article, decision)
            if state == "unchanged":
                continue
            review: EditorialReview = article.reviews[0]
            article.status = decision.article_state
            article.reviewed_at = decision.reviewed_at
            article.published_at = decision.published_at
            article.updated_at = decision.published_at
            review.status = decision.review_state
            review.reviewer_name = TRANSFER_REVIEWER_NAME
            review.decision_reason = None
            review.decided_at = decision.decided_at
            article.status = "approved"
            session.flush()
            publish_discovery_article(
                session,
                article.id,
                TRANSFER_REVIEWER_NAME,
                commit=False,
                published_at=decision.published_at,
            )
            transferred += 1
        session.flush()
        final_published = session.scalar(
            select(func.count())
            .select_from(DiscoveryArticle)
            .where(
                DiscoveryArticle.status == "published",
                DiscoveryArticle.published_at.is_not(None),
            )
        )
        final_approved = session.scalar(
            select(func.count())
            .select_from(EditorialReview)
            .where(
                EditorialReview.discovery_article_id.is_not(None),
                EditorialReview.status == "approved",
            )
        )
        if final_published != EXPECTED_DISCOVERY_COUNT or final_approved != 30:
            raise ValueError("final accepted Discovery state is incomplete")
        session.commit()
    except Exception:
        session.rollback()
        raise
    return AcceptedTransferSummary(
        created=created,
        transferred=transferred,
        unchanged=EXPECTED_DISCOVERY_COUNT - transferred,
        verified=EXPECTED_DISCOVERY_COUNT,
        dry_run=False,
        corpus_checksum=manifest.corpus_checksum,
        manifest_checksum=manifest.manifest_checksum,
    )
