from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from backend.app.domains.discovery.corpus import CuratedDiscoveryCorpus
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryArticlePlant,
    DiscoveryArticleSource,
    DiscoveryEvent,
    EditorialReview,
    PlantProfile,
    SourceRecord,
)
from backend.app.models.source import Source
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CuratedImportSummary:
    created: int
    unchanged: int
    reviews_created: int
    source_records_created: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _body_blocks(article) -> list[dict]:
    fields = (
        ("overview", "Overview", article.standfirst),
        (
            "research_question",
            "The discovery or research question",
            article.research_question,
        ),
        ("why_studied", "Why this plant was studied", article.research_context),
        ("methods", "What the researchers did", article.study_design),
        ("evidence_base", "Who or what was studied", article.evidence_base),
        ("findings", "What the study found", " ".join(article.main_findings)),
        ("why_matters", "Why the findings matter", article.why_matters),
        (
            "evidence_strength",
            "How strong the evidence is",
            article.evidence_strength_rationale,
        ),
        ("limitations", "Important limitations", " ".join(article.limitations)),
        ("safety", "Safety and risk context", article.safety_context),
        (
            "cannot_conclude",
            "What the research does not prove",
            " ".join(article.cannot_conclude),
        ),
    )
    blocks = [
        {
            "key": key,
            "heading": heading,
            "text": text,
            "source_ids": article.section_sources[key].source_ids,
            "evidence_locations": article.section_sources[key].evidence_locations,
        }
        for key, heading, text in fields
        if text
    ]
    blocks.extend(section.model_dump() for section in article.additional_sections)
    return blocks


def _validate_profile_media(profile: PlantProfile, caption: str) -> dict:
    image = dict(profile.hero_image or {})
    required = {
        "local_path",
        "source_page",
        "license",
        "license_url",
        "attribution",
        "checksum_sha256",
    }
    if not required <= image.keys() or any(not image[key] for key in required):
        raise ValueError(
            f"Plant profile {profile.slug} lacks reusable licensed media metadata."
        )
    image["caption"] = caption
    image["reuse_context"] = "curated_discovery"
    return image


def _validated_media(article, profile: PlantProfile | None) -> dict:
    if article.hero_image is not None:
        return article.hero_image.model_dump(mode="json")
    if profile is None or article.image_caption is None:
        raise ValueError(f"Discovery {article.slug} lacks licensed media metadata.")
    return _validate_profile_media(profile, article.image_caption)


def _source_record(
    session: Session, registry_source: Source, item, now: datetime
) -> tuple[SourceRecord, bool]:
    existing = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source_id == registry_source.id,
            SourceRecord.external_identifier == item.stable_identifier,
        )
    )
    if existing is not None:
        if (
            existing.canonical_url != str(item.canonical_url)
            or existing.doi != item.doi
            or existing.title != item.title
        ):
            raise ValueError(f"Existing source metadata differs for {item.source_id}.")
        return existing, False
    content_hash = hashlib.sha256(
        json.dumps(
            item.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    record = SourceRecord(
        source_id=registry_source.id,
        external_identifier=item.stable_identifier,
        url=str(item.canonical_url),
        canonical_url=str(item.canonical_url),
        title=item.title,
        publisher=registry_source.name,
        source_type=item.support_role,
        original_language="en",
        license_status=(
            "PubMed metadata; article and abstract copyright remain with their holders."
            if item.provider == "pubmed-eutils"
            else "Authoritative linked metadata; source terms remain applicable."
        ),
        supports={
            "discovery": True,
            "provider": item.provider,
            "curated": True,
            "support_role": item.support_role,
            "publication_types": item.publication_types,
            "retraction_status": item.retraction_status,
        },
        permitted_extract=None,
        parser_version="curated-source-metadata-v2",
        content_hash=content_hash,
        source_publication_date=item.publication_date,
        doi=item.doi,
        authors=item.authors,
        journal=item.journal,
        collected_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    return record, True


def import_curated_discoveries(
    session: Session, corpus: CuratedDiscoveryCorpus
) -> CuratedImportSummary:
    providers = {
        item.provider for article in corpus.articles for item in article.sources
    }
    registry_sources = {
        source.identifier: source
        for source in session.scalars(
            select(Source).where(Source.identifier.in_(providers))
        ).all()
    }
    missing_providers = sorted(providers - registry_sources.keys())
    if missing_providers:
        raise ValueError(
            f"Required source providers are missing: {', '.join(missing_providers)}"
        )
    requested_profile_slugs = {
        item.plant_slug for item in corpus.articles if item.plant_slug is not None
    }
    profiles = {
        profile.slug: profile
        for profile in session.scalars(
            select(PlantProfile).where(PlantProfile.slug.in_(requested_profile_slugs))
        ).all()
    }
    missing = sorted(requested_profile_slugs - profiles.keys())
    if missing:
        raise ValueError(
            f"Required published plant profiles are missing: {', '.join(missing)}"
        )
    for item in corpus.articles:
        profile = profiles.get(item.plant_slug) if item.plant_slug else None
        if profile is not None and profile.status != "published":
            raise ValueError(f"Plant profile {profile.slug} is not published.")
        _validated_media(item, profile)
        existing = session.scalar(
            select(DiscoveryArticle).where(DiscoveryArticle.slug == item.slug)
        )
        if (
            existing is not None
            and existing.version == item.content_version
            and existing.content_checksum != item.content_checksum
        ):
            raise ValueError(
                f"Refusing changed same-version curated content for {item.slug}."
            )
        if existing is not None and existing.version != item.content_version:
            raise ValueError(
                f"Refusing to overwrite existing curated version for {item.slug}."
            )
    created = unchanged = reviews_created = sources_created = 0
    now = _now()
    try:
        for item in corpus.articles:
            existing = session.scalar(
                select(DiscoveryArticle).where(DiscoveryArticle.slug == item.slug)
            )
            if existing is not None:
                unchanged += 1
                continue
            source_records = []
            for source_item in item.sources:
                source_record, source_created = _source_record(
                    session,
                    registry_sources[source_item.provider],
                    source_item,
                    now,
                )
                source_records.append((source_item, source_record))
                sources_created += int(source_created)
            primary_source = next(
                record
                for source_item, record in source_records
                if source_item.support_role == "primary_evidence"
            )
            event = DiscoveryEvent(
                source_record_id=primary_source.id,
                status="enriched",
                category=item.article_type,
                relevance_confidence=1.0,
                reasons=[
                    "curated_source_verified",
                    (
                        "linked_published_plant"
                        if item.plant_slug
                        else "standalone_botanical_identity_verified"
                    ),
                ],
                evidence_signals=[
                    "pubmed_identifier",
                    "section_level_traceability",
                    "authoritative_taxonomy",
                ],
                detected_entities=[
                    {
                        "common_name": item.common_name,
                        "scientific_name": item.scientific_name,
                        "plant_slug": item.plant_slug,
                        "family": (
                            item.botanical_identity.family
                            if item.botanical_identity
                            else None
                        ),
                        "ambiguous": False,
                    }
                ],
                evidence_package={
                    "origin": "curated",
                    "batch_id": corpus.batch_id,
                    "source_ids": [s.source_id for s in item.sources],
                    "botanical_identity": (
                        item.botanical_identity.model_dump(mode="json")
                        if item.botanical_identity
                        else None
                    ),
                    "section_sources": {
                        k: v.model_dump() for k, v in item.section_sources.items()
                    },
                },
                created_at=now,
                updated_at=now,
            )
            session.add(event)
            session.flush()
            profile = profiles.get(item.plant_slug) if item.plant_slug else None
            article = DiscoveryArticle(
                event_id=event.id,
                slug=item.slug,
                status="needs_review",
                headline=item.headline,
                standfirst=item.standfirst,
                body_blocks=_body_blocks(item),
                limitations=item.limitations,
                safety_context=item.safety_context,
                cannot_conclude=item.cannot_conclude,
                qa_payload={
                    "provider": "curated-corpus-schema-v1",
                    "passed": True,
                    "reason_codes": [],
                    "checks": {
                        "source_traceability": True,
                        "media_license": True,
                        "geography_evidence": True,
                        "botanical_identity": True,
                        "human_review_required": True,
                    },
                },
                content_checksum=item.content_checksum,
                version=item.content_version,
                content_origin="curated",
                article_type=item.article_type,
                research_date=item.research_date,
                research_question=item.research_question,
                research_context=item.research_context,
                study_design=item.study_design,
                evidence_base=item.evidence_base,
                intervention=item.intervention,
                comparator=item.comparator,
                main_findings=item.main_findings,
                evidence_strength=item.evidence_strength,
                evidence_strength_rationale=item.evidence_strength_rationale,
                why_matters=item.why_matters,
                practical_interpretation=item.practical_interpretation,
                section_sources={
                    k: v.model_dump() for k, v in item.section_sources.items()
                },
                hero_image=_validated_media(item, profile),
                geography=[g.model_dump(mode="json") for g in item.geography],
                created_at=now,
                updated_at=now,
            )
            session.add(article)
            session.flush()
            if profile is not None:
                session.add(
                    DiscoveryArticlePlant(
                        discovery_article_id=article.id, plant_profile_id=profile.id
                    )
                )
            for source_item, source_record in source_records:
                evidence_locations = [
                    {"section": key, "locations": trace.evidence_locations}
                    for key, trace in item.section_sources.items()
                    if source_item.source_id in trace.source_ids
                ]
                evidence_locations.extend(
                    {
                        "section": section.key,
                        "locations": section.evidence_locations,
                    }
                    for section in item.additional_sections
                    if source_item.source_id in section.source_ids
                )
                session.add(
                    DiscoveryArticleSource(
                        discovery_article_id=article.id,
                        source_record_id=source_record.id,
                        support_role=source_item.support_role,
                        evidence_locations=evidence_locations,
                    )
                )
            session.add(
                EditorialReview(
                    plant_profile_id=None,
                    discovery_article_id=article.id,
                    content_type="discovery_article",
                    status="needs_review",
                    review_payload={
                        "origin": "curated",
                        "batch_id": corpus.batch_id,
                        "version": item.content_version,
                        "content_checksum": item.content_checksum,
                        "source_ids": [s.source_id for s in item.sources],
                    },
                    created_at=now,
                )
            )
            created += 1
            reviews_created += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return CuratedImportSummary(
        created=created,
        unchanged=unchanged,
        reviews_created=reviews_created,
        source_records_created=sources_created,
    )
