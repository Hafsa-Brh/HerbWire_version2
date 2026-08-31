from datetime import datetime, timezone
from http import HTTPStatus
from uuid import UUID

from backend.app.domains.encyclopedia.corpus import (
    CorpusProfile,
    SourceManifest,
    load_corpus,
)
from backend.app.models.encyclopedia import (
    EditorialReview,
    PlantProfile,
    PlantProfileSource,
    SourceRecord,
    utc_now,
)
from backend.app.models.source import Source
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

ACCESS_DATE = "2026-08-31"
FIXED_TIME = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
PROTECTED_STATUSES = {"approved", "published"}


def _hash_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _get_or_create_source(session: Session, item: SourceManifest) -> Source:
    source = session.scalar(
        select(Source).where(Source.identifier == item.source_identifier)
    )
    if source is None:
        source = Source(
            identifier=item.source_identifier,
            name=item.source_name,
            base_url=str(item.base_url),
            status="approved",
            created_at=FIXED_TIME,
            updated_at=FIXED_TIME,
        )
        session.add(source)
        session.flush()
    else:
        source.name = item.source_name
        source.base_url = str(item.base_url)
        source.status = "approved"
    return source


def _get_or_create_source_record(
    session: Session, item: SourceManifest
) -> SourceRecord:
    source = _get_or_create_source(session, item)
    canonical_url = str(item.canonical_url)
    record = session.scalar(
        select(SourceRecord).where(SourceRecord.canonical_url == canonical_url)
    )
    values = {
        "source_id": source.id,
        "external_identifier": item.external_identifier,
        "url": str(item.url),
        "canonical_url": canonical_url,
        "title": item.title,
        "publisher": item.publisher,
        "source_type": item.source_type,
        "original_language": "en",
        "license_status": item.license_status,
        "supports": item.supports,
        "permitted_extract": item.provenance_notes,
        "parser_version": "curated-corpus-v2",
        "content_hash": _hash_text(
            f"{canonical_url}|{item.title}|{item.provenance_notes}"
        ),
        "source_publication_date": item.source_publication_date,
        "updated_at": FIXED_TIME,
    }
    if record is None:
        record = SourceRecord(
            **values,
            collected_at=FIXED_TIME,
            created_at=FIXED_TIME,
        )
        session.add(record)
        session.flush()
    else:
        for field, value in values.items():
            setattr(record, field, value)
    return record


def _profile_values(item: CorpusProfile) -> dict:
    return {
        "accepted_scientific_name": item.accepted_scientific_name,
        "botanical_author": item.botanical_author,
        "taxon_identifier": item.taxon_identifier,
        "known_synonyms": item.synonyms,
        "display_common_name": item.common_name,
        "family_name": item.family,
        "diversity_tags": item.diversity_tags,
        "summary": item.summary,
        "introduction": item.introduction,
        "botanical_description": item.botanical_description,
        "traditional_uses": item.traditional_uses,
        "parts_used": item.parts_used,
        "distribution": [
            region.model_dump(mode="json") for region in item.distribution
        ],
        "distribution_summary": item.distribution_summary,
        "growth_form": item.growth_form,
        "biome": item.biome,
        "preparation": item.preparation,
        "safety_notes": item.safety_notes,
        "evidence_notes": item.evidence_notes,
        "readiness_status": item.readiness_status,
        "readiness_reason": item.hold_reason,
        "hero_image": item.media.model_dump(mode="json"),
    }


def seed_curated_profiles(session: Session, batch: str | None = None) -> dict[str, int]:
    manifest = load_corpus()
    source_by_id = {source.external_identifier: source for source in manifest.sources}
    selected = [
        item for item in manifest.profiles if batch is None or item.batch == batch
    ]
    if batch is not None and batch not in {"A", "B", "C"}:
        raise ValueError("batch must be A, B, or C")

    created = 0
    updated = 0
    protected = 0
    source_links_created = 0

    for item in selected:
        values = _profile_values(item)
        profile = session.scalar(
            select(PlantProfile).where(PlantProfile.slug == item.slug)
        )
        if profile is None:
            status = "held" if item.readiness_status == "held" else "needs_review"
            profile = PlantProfile(
                slug=item.slug,
                status=status,
                version=item.content_version,
                approved_at=None,
                published_at=None,
                last_reviewed_at=None,
                created_at=FIXED_TIME,
                updated_at=FIXED_TIME,
                **values,
            )
            session.add(profile)
            session.flush()
            created += 1
        else:
            metadata_fields = {
                "accepted_scientific_name",
                "botanical_author",
                "taxon_identifier",
                "known_synonyms",
                "display_common_name",
                "family_name",
                "diversity_tags",
                "distribution",
                "distribution_summary",
                "growth_form",
                "biome",
                "readiness_status",
                "readiness_reason",
                "hero_image",
            }
            for field in metadata_fields:
                setattr(profile, field, values[field])
            if profile.status in PROTECTED_STATUSES:
                protected += 1
            elif item.content_version > profile.version:
                for field, value in values.items():
                    setattr(profile, field, value)
                profile.version = item.content_version
                profile.updated_at = FIXED_TIME
                updated += 1
            if profile.status in {"collected", "normalized", "draft"}:
                profile.status = "needs_review"

        existing_review = session.scalar(
            select(EditorialReview).where(
                EditorialReview.plant_profile_id == profile.id,
                EditorialReview.content_type == "plant_profile",
            )
        )
        if existing_review is None:
            review_status = (
                "held" if item.readiness_status == "held" else "needs_review"
            )
            session.add(
                EditorialReview(
                    plant_profile_id=profile.id,
                    content_type="plant_profile",
                    status=review_status,
                    decision_reason=item.hold_reason,
                    review_payload={
                        "corpus_slug": profile.slug,
                        "source": "curated_corpus",
                        "batch": item.batch,
                        "content_version": item.content_version,
                        "access_date": ACCESS_DATE,
                    },
                    created_at=FIXED_TIME,
                )
            )

        for reference in item.source_refs:
            source_item = source_by_id[reference.source_id]
            record = _get_or_create_source_record(session, source_item)
            link = session.scalar(
                select(PlantProfileSource).where(
                    PlantProfileSource.plant_profile_id == profile.id,
                    PlantProfileSource.source_record_id == record.id,
                    PlantProfileSource.support_role == reference.support_role,
                )
            )
            if link is None:
                session.add(
                    PlantProfileSource(
                        plant_profile_id=profile.id,
                        source_record_id=record.id,
                        support_role=reference.support_role,
                        note=reference.provenance_notes,
                    )
                )
                source_links_created += 1
            else:
                link.note = reference.provenance_notes

    session.commit()
    return {
        "profiles_created": created,
        "profiles_updated": updated,
        "profiles_protected": protected,
        "profiles_total": session.scalar(select(func.count(PlantProfile.id))) or 0,
        "source_records_total": session.scalar(select(func.count(SourceRecord.id)))
        or 0,
        "source_links_created": source_links_created,
    }


def list_published_profiles(
    session: Session,
    query: str | None = None,
    family: str | None = None,
    tag: str | None = None,
    page: int = 1,
    page_size: int = 12,
) -> tuple[list[PlantProfile], int]:
    filters = [PlantProfile.status == "published"]
    if query:
        needle = f"%{query.strip().lower()}%"
        filters.append(
            or_(
                func.lower(PlantProfile.display_common_name).like(needle),
                func.lower(PlantProfile.accepted_scientific_name).like(needle),
            )
        )
    if family:
        filters.append(func.lower(PlantProfile.family_name) == family.strip().lower())
    if tag:
        filters.append(PlantProfile.diversity_tags.contains([tag]))

    total = session.scalar(select(func.count(PlantProfile.id)).where(*filters)) or 0
    statement = (
        select(PlantProfile)
        .where(*filters)
        .options(
            selectinload(PlantProfile.sources).selectinload(
                PlantProfileSource.source_record
            )
        )
        .order_by(PlantProfile.display_common_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(session.scalars(statement).all()), total


def get_published_profile(session: Session, slug: str) -> PlantProfile:
    profile = session.scalar(
        select(PlantProfile)
        .where(PlantProfile.slug == slug, PlantProfile.status == "published")
        .options(
            selectinload(PlantProfile.sources).selectinload(
                PlantProfileSource.source_record
            )
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Plant profile not found."
        )
    return profile


def list_reviews(session: Session) -> list[EditorialReview]:
    return list(
        session.scalars(
            select(EditorialReview)
            .options(selectinload(EditorialReview.plant_profile))
            .order_by(EditorialReview.created_at.desc())
        ).all()
    )


def get_review(session: Session, review_id: UUID) -> EditorialReview:
    review = session.scalar(
        select(EditorialReview)
        .where(EditorialReview.id == review_id)
        .options(selectinload(EditorialReview.plant_profile))
    )
    if review is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review item not found."
        )
    return review


def approve_review(
    session: Session, review_id: UUID, reviewer_name: str
) -> EditorialReview:
    review = get_review(session, review_id)
    if review.status not in {"needs_review", "held"}:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Review cannot be approved from its current state.",
        )
    if (
        review.plant_profile is None
        or review.plant_profile.readiness_status != "ready_for_review"
    ):
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Only complete profiles marked ready for review can be approved.",
        )
    review.status = "approved"
    review.reviewer_name = reviewer_name
    review.decided_at = utc_now()
    review.plant_profile.status = "approved"
    review.plant_profile.approved_at = review.decided_at
    review.plant_profile.last_reviewed_at = review.decided_at
    session.commit()
    session.refresh(review)
    return review


def reject_review(
    session: Session, review_id: UUID, reason: str, reviewer_name: str
) -> EditorialReview:
    if not reason.strip():
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="A rejection or hold reason is required.",
        )
    review = get_review(session, review_id)
    if review.status == "approved":
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Approved reviews cannot be rejected.",
        )
    review.status = "held"
    review.reviewer_name = reviewer_name
    review.decision_reason = reason.strip()
    review.decided_at = utc_now()
    if review.plant_profile is not None:
        review.plant_profile.status = "held"
    session.commit()
    session.refresh(review)
    return review


def publish_profile(session: Session, profile_id: UUID) -> PlantProfile:
    profile = session.scalar(
        select(PlantProfile)
        .where(PlantProfile.id == profile_id)
        .options(selectinload(PlantProfile.sources))
    )
    if profile is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Plant profile not found."
        )
    if profile.status != "approved" or profile.approved_at is None:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Only approved profiles can be published.",
        )
    if not profile.sources:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Published profiles require at least one provenance source.",
        )
    if not profile.safety_notes:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Published profiles require safety notes.",
        )
    media = profile.hero_image
    if (
        profile.readiness_status != "ready_for_review"
        or not profile.evidence_notes
        or not profile.distribution
        or media.get("kind") != "licensed_photograph"
        or not media.get("local_path")
        or not media.get("license")
        or not media.get("attribution")
        or not media.get("checksum_sha256")
    ):
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Published profiles must pass corpus readiness checks.",
        )
    profile.status = "published"
    profile.published_at = utc_now()
    session.commit()
    session.refresh(profile)
    return profile
