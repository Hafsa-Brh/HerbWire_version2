from backend.app.api.schemas import (
    PlantDetailResponse,
    PlantListItemResponse,
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
        display_common_name=profile.display_common_name,
        family_name=profile.family_name,
        summary=profile.summary,
        status=profile.status,
        hero_image=profile.hero_image,
        published_at=profile.published_at,
        source_count=len(profile.sources),
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


@router.get("/plants", response_model=list[PlantListItemResponse])
def read_plants(
    query: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
) -> list[PlantListItemResponse]:
    return [
        plant_list_item(profile) for profile in list_published_profiles(session, query)
    ]


@router.get("/plants/{slug}", response_model=PlantDetailResponse)
def read_plant(
    slug: str, session: Session = Depends(get_session)
) -> PlantDetailResponse:
    return plant_detail(get_published_profile(session, slug))
