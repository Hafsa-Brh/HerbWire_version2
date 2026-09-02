from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from backend.app.domains.discovery.corpus import CuratedDiscoveryCorpus
from backend.app.domains.discovery.deduplication import require_pubmed_source
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryArticlePlant,
    DiscoveryArticleSource,
    DiscoveryEvent,
    EditorialReview,
    PlantProfile,
    SourceRecord,
)
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
    return [
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


def _source_record(
    session: Session, source, item, now: datetime
) -> tuple[SourceRecord, bool]:
    existing = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source_id == source.id,
            SourceRecord.external_identifier == item.pmid,
        )
    )
    if existing is not None:
        if (
            existing.canonical_url != str(item.canonical_url)
            or existing.doi != item.doi
            or existing.title != item.title
        ):
            raise ValueError(f"Existing PubMed metadata differs for PMID {item.pmid}.")
        return existing, False
    content_hash = hashlib.sha256(
        json.dumps(
            item.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    record = SourceRecord(
        source_id=source.id,
        external_identifier=item.pmid,
        url=str(item.canonical_url),
        canonical_url=str(item.canonical_url),
        title=item.title,
        publisher="National Library of Medicine (PubMed)",
        source_type="scientific_literature",
        original_language="en",
        license_status=(
            "PubMed metadata; article and abstract copyright remain with their holders."
        ),
        supports={
            "discovery": True,
            "provider": "pubmed",
            "curated": True,
            "publication_types": item.publication_types,
            "retraction_status": item.retraction_status,
        },
        permitted_extract=None,
        parser_version="curated-pubmed-metadata-v1",
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
    source = require_pubmed_source(session)
    profiles = {
        profile.slug: profile
        for profile in session.scalars(
            select(PlantProfile).where(
                PlantProfile.slug.in_([item.plant_slug for item in corpus.articles])
            )
        ).all()
    }
    missing = sorted({item.plant_slug for item in corpus.articles} - profiles.keys())
    if missing:
        raise ValueError(
            f"Required published plant profiles are missing: {', '.join(missing)}"
        )
    for item in corpus.articles:
        profile = profiles[item.plant_slug]
        if profile.status != "published":
            raise ValueError(f"Plant profile {profile.slug} is not published.")
        _validate_profile_media(profile, item.image_caption)
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
            source_record, source_created = _source_record(
                session, source, item.sources[0], now
            )
            sources_created += int(source_created)
            event = DiscoveryEvent(
                source_record_id=source_record.id,
                status="enriched",
                category=item.article_type,
                relevance_confidence=1.0,
                reasons=["curated_source_verified", "linked_published_plant"],
                evidence_signals=["pubmed_identifier", "section_level_traceability"],
                detected_entities=[
                    {
                        "common_name": item.common_name,
                        "scientific_name": item.scientific_name,
                        "plant_slug": item.plant_slug,
                        "ambiguous": False,
                    }
                ],
                evidence_package={
                    "origin": "curated",
                    "source_ids": [s.source_id for s in item.sources],
                    "section_sources": {
                        k: v.model_dump() for k, v in item.section_sources.items()
                    },
                },
                created_at=now,
                updated_at=now,
            )
            session.add(event)
            session.flush()
            profile = profiles[item.plant_slug]
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
                hero_image=_validate_profile_media(profile, item.image_caption),
                geography=[g.model_dump() for g in item.geography],
                created_at=now,
                updated_at=now,
            )
            session.add(article)
            session.flush()
            session.add(
                DiscoveryArticlePlant(
                    discovery_article_id=article.id, plant_profile_id=profile.id
                )
            )
            session.add(
                DiscoveryArticleSource(
                    discovery_article_id=article.id,
                    source_record_id=source_record.id,
                    support_role="primary_evidence",
                    evidence_locations=[
                        {"section": key, "locations": trace.evidence_locations}
                        for key, trace in item.section_sources.items()
                    ],
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
