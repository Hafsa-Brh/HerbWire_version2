# ruff: noqa: E501
from datetime import datetime, timezone
from http import HTTPStatus
from uuid import UUID

from backend.app.models.encyclopedia import (
    EditorialReview,
    PlantProfile,
    PlantProfileSource,
    SourceRecord,
    utc_now,
)
from backend.app.models.source import Source
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

ACCESS_DATE = "2026-08-30"
FIXED_TIME = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def _hash_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


CURATED_PLANTS = [
    {
        "slug": "german-chamomile",
        "accepted_scientific_name": "Matricaria chamomilla L.",
        "display_common_name": "German chamomile",
        "family_name": "Asteraceae",
        "summary": "A widely cultivated aromatic annual used in documented herbal traditions, especially for flower preparations.",
        "introduction": "German chamomile is presented here as reviewed encyclopedia content, not as medical advice. Its profile distinguishes traditional use from clinical efficacy and links each claim area to stored sources.",
        "botanical_description": "Kew Plants of the World Online treats Matricaria chamomilla L. as an accepted annual species in temperate biomes.",
        "traditional_uses": [
            {
                "tradition": "European herbal medicine / EMA HMPC",
                "statement": "Matricaria flower preparations are documented for traditional medicinal use in minor gastrointestinal complaints and mild skin or mouth inflammations in the EMA herbal medicine record.",
                "limitation": "This documents traditional-use framing; it is not personalized treatment advice or a cure claim.",
            }
        ],
        "parts_used": ["flower"],
        "distribution": [
            "Macaronesia",
            "North Africa",
            "temperate Eurasia",
            "Indo-China",
        ],
        "preparation": "Documented traditions commonly center on dried flower preparations such as infusions. No individualized dosage is provided by HerbWire.",
        "safety_notes": [
            "NCCIH describes chamomile as likely safe in amounts commonly found in teas and foods, while noting possible side effects and allergy concerns.",
            "People with allergies to related plants such as ragweed should be cautious; professional advice is appropriate for pregnancy, medicines, or serious conditions.",
        ],
        "evidence_notes": "The cited sources support taxonomy, documented traditional-use context, and safety cautions. HerbWire does not present chamomile as proven to cure disease.",
        "hero_image": {
            "kind": "local_placeholder",
            "label": "Botanical placeholder for German chamomile",
            "license_status": "No external image used; replace only after media license review.",
            "attribution": "HerbWire local placeholder",
            "alt_text": "Stylized botanical placeholder for German chamomile flowers",
        },
        "sources": [
            {
                "source_identifier": "kew-powo",
                "source_name": "Plants of the World Online, Royal Botanic Gardens, Kew",
                "base_url": "https://powo.science.kew.org/",
                "external_identifier": "powo-matricaria-chamomilla",
                "url": "https://powo.science.kew.org/taxon/urn%3Alsid%3Aipni.org%3Anames%3A154715-2/general-information",
                "canonical_url": "https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:154715-2/general-information",
                "title": "Matricaria chamomilla L.",
                "publisher": "Royal Botanic Gardens, Kew",
                "source_type": "taxonomy_distribution",
                "license_status": "Citation and paraphrase only; page reuse terms not treated as blanket content license.",
                "supports": {"taxonomy": True, "distribution": True},
                "support_role": "taxonomy_distribution",
                "permitted_extract": "Accepted species; native range and annual habit verified from POWO summary.",
            },
            {
                "source_identifier": "ema-herbal",
                "source_name": "European Medicines Agency herbal medicinal products",
                "base_url": "https://www.ema.europa.eu/",
                "external_identifier": "ema-matricariae-flos",
                "url": "https://www.ema.europa.eu/en/medicines/herbal/matricariae-flos",
                "canonical_url": "https://www.ema.europa.eu/en/medicines/herbal/matricariae-flos",
                "title": "Matricariae flos - herbal medicinal product",
                "publisher": "European Medicines Agency",
                "source_type": "traditional_use_safety",
                "license_status": "Citation and paraphrase only; official public page.",
                "supports": {"traditional_use": True, "safety": True},
                "support_role": "traditional_use_safety",
                "permitted_extract": "EMA herbal record used only for high-level traditional-use paraphrase.",
            },
            {
                "source_identifier": "nccih",
                "source_name": "National Center for Complementary and Integrative Health",
                "base_url": "https://www.nccih.nih.gov/",
                "external_identifier": "nccih-chamomile",
                "url": "https://www.nccih.nih.gov/health/chamomile",
                "canonical_url": "https://www.nccih.nih.gov/health/chamomile",
                "title": "Chamomile: Usefulness and Safety",
                "publisher": "NCCIH",
                "source_type": "safety",
                "license_status": "U.S. government health information cited and paraphrased.",
                "supports": {"safety": True, "evidence_limits": True},
                "support_role": "safety",
                "permitted_extract": "Safety summary paraphrases NCCIH public health information.",
            },
        ],
    },
    {
        "slug": "peppermint",
        "accepted_scientific_name": "Mentha x piperita L.",
        "display_common_name": "Peppermint",
        "family_name": "Lamiaceae",
        "summary": "A cultivated mint hybrid whose leaf and oil have documented herbal-medicine uses and safety cautions.",
        "introduction": "Peppermint is handled as reviewed encyclopedia content with separate taxonomy, traditional-use, and safety provenance.",
        "botanical_description": "Kew treats Mentha x piperita L. as an accepted hybrid, with Mentha aquatica x Mentha spicata as the hybrid formula.",
        "traditional_uses": [
            {
                "tradition": "European herbal medicine / EMA HMPC",
                "statement": "EMA records peppermint oil and peppermint leaf as herbal medicinal products with documented use contexts, including gastrointestinal symptom framing for peppermint oil.",
                "limitation": "This profile does not provide product directions, individualized dosing, or treatment claims.",
            }
        ],
        "parts_used": ["leaf", "essential oil"],
        "distribution": [
            "Europe",
            "Central Asia",
            "widely cultivated in temperate regions",
        ],
        "preparation": "Traditional preparations include leaf infusions and separately regulated peppermint oil preparations. Essential oils are concentrated and are not interchangeable with household tea.",
        "safety_notes": [
            "NCCIH notes possible oral peppermint-oil side effects including heartburn, nausea, abdominal pain, and dry mouth, and rare allergic reactions.",
            "Peppermint oil should be treated cautiously around young children and sensitive populations; HerbWire does not advise ingestion of essential oils.",
        ],
        "evidence_notes": "The sources support hybrid identity, selected distribution, documented herbal-use context, and safety cautions. Traditional use is not rendered as proven efficacy.",
        "hero_image": {
            "kind": "local_placeholder",
            "label": "Botanical placeholder for peppermint",
            "license_status": "No external image used; replace only after media license review.",
            "attribution": "HerbWire local placeholder",
            "alt_text": "Stylized botanical placeholder for peppermint leaves",
        },
        "sources": [
            {
                "source_identifier": "kew-powo",
                "source_name": "Plants of the World Online, Royal Botanic Gardens, Kew",
                "base_url": "https://powo.science.kew.org/",
                "external_identifier": "powo-mentha-piperita",
                "url": "https://powo.science.kew.org/taxon/urn%3Alsid%3Aipni.org%3Anames%3A450969-1",
                "canonical_url": "https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:450969-1",
                "title": "Mentha x piperita L.",
                "publisher": "Royal Botanic Gardens, Kew",
                "source_type": "taxonomy_distribution",
                "license_status": "Citation and paraphrase only; page reuse terms not treated as blanket content license.",
                "supports": {"taxonomy": True, "distribution": True},
                "support_role": "taxonomy_distribution",
                "permitted_extract": "Accepted hybrid and range verified from POWO summary.",
            },
            {
                "source_identifier": "ema-herbal",
                "source_name": "European Medicines Agency herbal medicinal products",
                "base_url": "https://www.ema.europa.eu/",
                "external_identifier": "ema-menthae-piperitae-aetheroleum",
                "url": "https://www.ema.europa.eu/en/medicines/herbal/menthae-piperitae-aetheroleum",
                "canonical_url": "https://www.ema.europa.eu/en/medicines/herbal/menthae-piperitae-aetheroleum",
                "title": "Menthae piperitae aetheroleum - herbal medicinal product",
                "publisher": "European Medicines Agency",
                "source_type": "traditional_use_safety",
                "license_status": "Citation and paraphrase only; official public page.",
                "supports": {"traditional_use": True, "safety": True},
                "support_role": "traditional_use_safety",
                "permitted_extract": "EMA herbal record used only for high-level traditional-use paraphrase.",
            },
            {
                "source_identifier": "nccih",
                "source_name": "National Center for Complementary and Integrative Health",
                "base_url": "https://www.nccih.nih.gov/",
                "external_identifier": "nccih-peppermint-oil",
                "url": "https://www.nccih.nih.gov/health/peppermint-oil",
                "canonical_url": "https://www.nccih.nih.gov/health/peppermint-oil",
                "title": "Peppermint Oil: Usefulness and Safety",
                "publisher": "NCCIH",
                "source_type": "safety",
                "license_status": "U.S. government health information cited and paraphrased.",
                "supports": {"safety": True, "evidence_limits": True},
                "support_role": "safety",
                "permitted_extract": "Safety summary paraphrases NCCIH public health information.",
            },
        ],
    },
    {
        "slug": "ginger",
        "accepted_scientific_name": "Zingiber officinale Roscoe",
        "display_common_name": "Ginger",
        "family_name": "Zingiberaceae",
        "summary": "A rhizomatous tropical plant whose rhizome is used as a spice and appears in documented herbal-medicine traditions.",
        "introduction": "Ginger is included as reviewed encyclopedia content with provenance for taxonomy, distribution, traditional-use framing, and safety limits.",
        "botanical_description": "Kew describes Zingiber officinale Roscoe as an accepted rhizomatous geophyte associated with seasonally dry tropical biome contexts.",
        "traditional_uses": [
            {
                "tradition": "European herbal medicine / EMA HMPC",
                "statement": "EMA records ginger rhizome as an herbal medicinal product and documents traditional-use framing for nausea and mild gastrointestinal contexts.",
                "limitation": "This does not replace professional care and is not individualized dosage or treatment advice.",
            }
        ],
        "parts_used": ["rhizome"],
        "distribution": [
            "Eastern Himalaya",
            "South-Central China",
            "widely cultivated tropical and subtropical regions",
        ],
        "preparation": "Documented food and herbal traditions use the rhizome fresh, dried, powdered, or infused. HerbWire does not provide dosage instructions.",
        "safety_notes": [
            "NCCIH notes ginger may have side effects such as abdominal discomfort, heartburn, diarrhea, and mouth or throat irritation.",
            "People who are pregnant, use medicines, or have medical conditions should seek professional advice rather than relying on this encyclopedia profile.",
        ],
        "evidence_notes": "The sources support taxonomy, rhizome identity, documented herbal-use context, and safety cautions. HerbWire avoids cure claims.",
        "hero_image": {
            "kind": "local_placeholder",
            "label": "Botanical placeholder for ginger",
            "license_status": "No external image used; replace only after media license review.",
            "attribution": "HerbWire local placeholder",
            "alt_text": "Stylized botanical placeholder for ginger rhizome and leaves",
        },
        "sources": [
            {
                "source_identifier": "kew-powo",
                "source_name": "Plants of the World Online, Royal Botanic Gardens, Kew",
                "base_url": "https://powo.science.kew.org/",
                "external_identifier": "powo-zingiber-officinale",
                "url": "https://powo.science.kew.org/taxon/urn%3Alsid%3Aipni.org%3Anames%3A798372-1",
                "canonical_url": "https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:798372-1",
                "title": "Zingiber officinale Roscoe",
                "publisher": "Royal Botanic Gardens, Kew",
                "source_type": "taxonomy_distribution",
                "license_status": "Citation and paraphrase only; page reuse terms not treated as blanket content license.",
                "supports": {"taxonomy": True, "distribution": True},
                "support_role": "taxonomy_distribution",
                "permitted_extract": "Accepted species, rhizomatous habit, and range verified from POWO summary.",
            },
            {
                "source_identifier": "ema-herbal",
                "source_name": "European Medicines Agency herbal medicinal products",
                "base_url": "https://www.ema.europa.eu/",
                "external_identifier": "ema-zingiberis-rhizoma",
                "url": "https://www.ema.europa.eu/en/medicines/herbal/zingiberis-rhizoma",
                "canonical_url": "https://www.ema.europa.eu/en/medicines/herbal/zingiberis-rhizoma",
                "title": "Zingiberis rhizoma - herbal medicinal product",
                "publisher": "European Medicines Agency",
                "source_type": "traditional_use_safety",
                "license_status": "Citation and paraphrase only; official public page.",
                "supports": {"traditional_use": True, "safety": True},
                "support_role": "traditional_use_safety",
                "permitted_extract": "EMA herbal record used only for high-level traditional-use paraphrase.",
            },
            {
                "source_identifier": "nccih",
                "source_name": "National Center for Complementary and Integrative Health",
                "base_url": "https://www.nccih.nih.gov/",
                "external_identifier": "nccih-ginger",
                "url": "https://www.nccih.nih.gov/health/ginger",
                "canonical_url": "https://www.nccih.nih.gov/health/ginger",
                "title": "Ginger: Usefulness and Safety",
                "publisher": "NCCIH",
                "source_type": "safety",
                "license_status": "U.S. government health information cited and paraphrased.",
                "supports": {"safety": True, "evidence_limits": True},
                "support_role": "safety",
                "permitted_extract": "Safety summary paraphrases NCCIH public health information.",
            },
        ],
    },
]


def _get_or_create_source(session: Session, item: dict) -> Source:
    source = session.scalar(
        select(Source).where(Source.identifier == item["source_identifier"])
    )
    if source is None:
        source = Source(
            identifier=item["source_identifier"],
            name=item["source_name"],
            base_url=item["base_url"],
            status="approved",
            created_at=FIXED_TIME,
            updated_at=FIXED_TIME,
        )
        session.add(source)
        session.flush()
    else:
        source.name = item["source_name"]
        source.base_url = item["base_url"]
        source.status = "approved"
    return source


def _get_or_create_source_record(session: Session, item: dict) -> SourceRecord:
    source = _get_or_create_source(session, item)
    record = session.scalar(
        select(SourceRecord).where(SourceRecord.canonical_url == item["canonical_url"])
    )
    if record is None:
        record = SourceRecord(
            source_id=source.id,
            external_identifier=item["external_identifier"],
            url=item["url"],
            canonical_url=item["canonical_url"],
            title=item["title"],
            publisher=item["publisher"],
            source_type=item["source_type"],
            original_language="en",
            license_status=item["license_status"],
            supports=item["supports"],
            permitted_extract=item["permitted_extract"],
            parser_version="curated-seed-v1",
            content_hash=_hash_text(item["canonical_url"]),
            source_publication_date=None,
            collected_at=FIXED_TIME,
            created_at=FIXED_TIME,
            updated_at=FIXED_TIME,
        )
        session.add(record)
        session.flush()
    return record


def seed_curated_profiles(session: Session) -> dict[str, int]:
    profiles_created = 0

    for item in CURATED_PLANTS:
        profile = session.scalar(
            select(PlantProfile).where(PlantProfile.slug == item["slug"])
        )
        if profile is None:
            profile = PlantProfile(
                slug=item["slug"],
                status="needs_review",
                accepted_scientific_name=item["accepted_scientific_name"],
                display_common_name=item["display_common_name"],
                family_name=item["family_name"],
                summary=item["summary"],
                introduction=item["introduction"],
                botanical_description=item["botanical_description"],
                traditional_uses=item["traditional_uses"],
                parts_used=item["parts_used"],
                distribution=item["distribution"],
                preparation=item["preparation"],
                safety_notes=item["safety_notes"],
                evidence_notes=item["evidence_notes"],
                hero_image=item["hero_image"],
                version=1,
                approved_at=None,
                published_at=None,
                last_reviewed_at=None,
                created_at=FIXED_TIME,
                updated_at=FIXED_TIME,
            )
            session.add(profile)
            session.flush()
            profiles_created += 1
        else:
            for field in (
                "accepted_scientific_name",
                "display_common_name",
                "family_name",
                "summary",
                "introduction",
                "botanical_description",
                "traditional_uses",
                "parts_used",
                "distribution",
                "preparation",
                "safety_notes",
                "evidence_notes",
                "hero_image",
            ):
                setattr(profile, field, item[field])
            if profile.status in {"collected", "normalized", "draft"}:
                profile.status = "needs_review"

        existing_review = session.scalar(
            select(EditorialReview).where(
                EditorialReview.plant_profile_id == profile.id,
                EditorialReview.content_type == "plant_profile",
            )
        )
        if existing_review is None:
            session.add(
                EditorialReview(
                    plant_profile_id=profile.id,
                    content_type="plant_profile",
                    status="needs_review",
                    review_payload={
                        "seed_slug": profile.slug,
                        "source": "curated_seed",
                        "access_date": ACCESS_DATE,
                    },
                    created_at=FIXED_TIME,
                )
            )

        for source_item in item["sources"]:
            record = _get_or_create_source_record(session, source_item)
            exists = session.scalar(
                select(PlantProfileSource).where(
                    PlantProfileSource.plant_profile_id == profile.id,
                    PlantProfileSource.source_record_id == record.id,
                    PlantProfileSource.support_role == source_item["support_role"],
                )
            )
            if exists is None:
                session.add(
                    PlantProfileSource(
                        plant_profile_id=profile.id,
                        source_record_id=record.id,
                        support_role=source_item["support_role"],
                        note=f"Accessed {ACCESS_DATE}.",
                    )
                )

    session.commit()
    total_profiles = len(session.scalars(select(PlantProfile)).all())
    total_records = len(session.scalars(select(SourceRecord)).all())
    return {
        "profiles_created": profiles_created,
        "profiles_total": total_profiles,
        "source_records_total": total_records,
    }


def list_published_profiles(
    session: Session, query: str | None = None
) -> list[PlantProfile]:
    statement = (
        select(PlantProfile)
        .where(PlantProfile.status == "published")
        .options(
            selectinload(PlantProfile.sources).selectinload(
                PlantProfileSource.source_record
            )
        )
        .order_by(PlantProfile.display_common_name)
    )
    profiles = list(session.scalars(statement).all())
    if query:
        needle = query.casefold()
        profiles = [
            profile
            for profile in profiles
            if needle in profile.display_common_name.casefold()
            or needle in profile.accepted_scientific_name.casefold()
        ]
    return profiles


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
    review.status = "approved"
    review.reviewer_name = reviewer_name
    review.decided_at = utc_now()
    if review.plant_profile is not None:
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
    profile.status = "published"
    profile.published_at = utc_now()
    session.commit()
    session.refresh(profile)
    return profile
