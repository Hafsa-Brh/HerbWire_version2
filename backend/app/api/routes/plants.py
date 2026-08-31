from backend.app.api.schemas import (
    PlantDetailResponse,
    PlantListItemResponse,
    PlantPageResponse,
    SourceRecordResponse,
)
from backend.app.db.session import get_session
from backend.app.domains.encyclopedia.service import (
    get_published_profile,
    list_published_profiles,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter()


def _source_response(link) -> SourceRecordResponse:
    record = link.source_record
    return SourceRecordResponse(
        id=record.id,
        url=record.url,
        canonical_url=record.canonical_url,
        title=record.title,
        publisher=record.publisher,
        source_type=record.source_type,
        original_language=record.original_language,
        license_status=record.license_status,
        supports=record.supports,
        accessed_at=record.collected_at,
    )


def plant_list_item(profile) -> PlantListItemResponse:
    return PlantListItemResponse(
        id=profile.id,
        slug=profile.slug,
        accepted_scientific_name=profile.accepted_scientific_name,
        botanical_author=profile.botanical_author,
        taxon_identifier=profile.taxon_identifier,
        known_synonyms=profile.known_synonyms,
        display_common_name=profile.display_common_name,
        family_name=profile.family_name,
        diversity_tags=profile.diversity_tags,
        summary=profile.summary,
        status=profile.status,
        hero_image=profile.hero_image,
        published_at=profile.published_at,
        source_count=sum(
            link.source_record.source_type != "licensed_media"
            for link in profile.sources
        ),
        growth_form=profile.growth_form,
        biome=profile.biome,
        distribution_summary=profile.distribution_summary,
        readiness_status=profile.readiness_status,
    )


def plant_detail(profile) -> PlantDetailResponse:
    return PlantDetailResponse(
        **plant_list_item(profile).model_dump(),
        introduction=profile.introduction,
        botanical_description=profile.botanical_description,
        traditional_uses=profile.traditional_uses,
        parts_used=profile.parts_used,
        distribution=profile.distribution,
        preparation=profile.preparation,
        safety_notes=profile.safety_notes,
        evidence_notes=profile.evidence_notes,
        last_reviewed_at=profile.last_reviewed_at,
        sources=[_source_response(link) for link in profile.sources],
    )


@router.get("/plants", response_model=PlantPageResponse)
def read_plants(
    query: str | None = Query(default=None, min_length=1),
    family: str | None = Query(default=None, min_length=1),
    tag: str | None = Query(default=None, min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    session: Session = Depends(get_session),
) -> PlantPageResponse:
    profiles, total = list_published_profiles(
        session,
        query=query,
        family=family,
        tag=tag,
        page=page,
        page_size=page_size,
    )
    return PlantPageResponse(
        items=[plant_list_item(profile) for profile in profiles],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/plants/{slug}", response_model=PlantDetailResponse)
def read_plant(
    slug: str, session: Session = Depends(get_session)
) -> PlantDetailResponse:
    return plant_detail(get_published_profile(session, slug))
