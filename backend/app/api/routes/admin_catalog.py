from math import ceil
from typing import Literal
from urllib.parse import urlparse

from backend.app.api.admin_catalog_schemas import (
    AdminContentItemResponse,
    AdminContentPageResponse,
    AdminContentSummaryResponse,
    AdminSourceAssociationResponse,
    AdminSourceItemResponse,
    AdminSourcePageResponse,
)
from backend.app.core.auth import require_editor_session
from backend.app.db.session import get_session
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryArticlePlant,
    DiscoveryArticleSource,
    EditorialReview,
    PlantProfile,
    PlantProfileSource,
    SourceRecord,
)
from backend.app.models.materials import MaterialStory, MaterialStorySource
from backend.app.models.source import Source
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

router = APIRouter(prefix="/admin/catalog")


def require_editor(request: Request) -> None:
    require_editor_session(request)


def _page_bounds(total: int, page: int, page_size: int) -> tuple[int, int, int]:
    total_pages = max(1, ceil(total / page_size))
    normalized_page = min(max(page, 1), total_pages)
    return normalized_page, (normalized_page - 1) * page_size, total_pages


def _summary(session: Session) -> AdminContentSummaryResponse:
    published_plants = (
        session.scalar(
            select(func.count())
            .select_from(PlantProfile)
            .where(PlantProfile.status == "published")
        )
        or 0
    )
    published_discoveries = (
        session.scalar(
            select(func.count())
            .select_from(DiscoveryArticle)
            .where(DiscoveryArticle.status == "published")
        )
        or 0
    )
    published_materials = (
        session.scalar(
            select(func.count())
            .select_from(MaterialStory)
            .where(MaterialStory.status == "published")
        )
        or 0
    )
    source_records = session.scalar(select(func.count()).select_from(SourceRecord)) or 0
    plant_links = (
        session.scalar(select(func.count()).select_from(PlantProfileSource)) or 0
    )
    discovery_links = (
        session.scalar(select(func.count()).select_from(DiscoveryArticleSource)) or 0
    )
    material_links = (
        session.scalar(select(func.count()).select_from(MaterialStorySource)) or 0
    )
    needs_review = (
        session.scalar(
            select(func.count())
            .select_from(EditorialReview)
            .where(EditorialReview.status.in_(("needs_review", "held")))
        )
        or 0
    )
    return AdminContentSummaryResponse(
        total_content=published_plants + published_discoveries + published_materials,
        published_plants=published_plants,
        published_discoveries=published_discoveries,
        published_materials=published_materials,
        source_records=source_records,
        provenance_relationships=plant_links + discovery_links + material_links,
        needs_review=needs_review,
    )


def _plant_item(profile: PlantProfile) -> AdminContentItemResponse:
    return AdminContentItemResponse(
        id=profile.id,
        title=profile.display_common_name,
        content_type="plant_profile",
        content_type_label="Plant Profile",
        status=profile.status,
        timestamp=profile.published_at or profile.created_at,
        plant_identity=profile.accepted_scientific_name,
        source_count=len({link.source_record_id for link in profile.sources}),
        origin="curated corpus",
        public_path=f"/plants/{profile.slug}",
        editorial_path="/admin/reviews",
    )


def _discovery_item(article: DiscoveryArticle) -> AdminContentItemResponse:
    identity = article.event.evidence_package.get("botanical_identity") or {}
    linked = article.plant_links[0].plant_profile if article.plant_links else None
    common_name = identity.get("common_name") or (
        linked.display_common_name if linked else "Medicinal plant"
    )
    scientific_name = identity.get("accepted_scientific_name") or (
        linked.accepted_scientific_name if linked else ""
    )
    pmid = next(
        (
            link.source_record.external_identifier
            for link in article.sources
            if link.source_record.supports.get("provider")
            in {"pubmed", "pubmed-eutils"}
        ),
        None,
    )
    return AdminContentItemResponse(
        id=article.id,
        title=article.headline,
        content_type="discovery",
        content_type_label="Discovery",
        status=article.status,
        timestamp=article.published_at or article.created_at,
        plant_identity=f"{common_name} / {scientific_name}".rstrip(" /"),
        source_count=len({link.source_record_id for link in article.sources}),
        origin=f"{article.content_origin} corpus",
        public_path=f"/discoveries/{article.slug}",
        editorial_path=f"/admin/discoveries?article={article.id}",
        pmid=pmid,
    )


def _material_item(story: MaterialStory) -> AdminContentItemResponse:
    return AdminContentItemResponse(
        id=story.id,
        title=story.title,
        content_type="material_story",
        content_type_label="Material Story",
        status=story.status,
        timestamp=story.published_at or story.created_at,
        plant_identity=", ".join(story.material_labels),
        source_count=len({link.source_record_id for link in story.sources}),
        origin="curated corpus",
        public_path=f"/materials-and-craft/{story.slug}",
        editorial_path=f"/materials-and-craft/{story.slug}",
    )


@router.get(
    "/content",
    response_model=AdminContentPageResponse,
    dependencies=[Depends(require_editor)],
)
def content_catalog(
    query: str | None = Query(default=None, max_length=120),
    content_type: Literal["plant_profile", "discovery", "material_story"] | None = None,
    editorial_status: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1),
    page_size: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> AdminContentPageResponse:
    profiles = list(
        session.scalars(
            select(PlantProfile)
            .options(selectinload(PlantProfile.sources))
            .order_by(PlantProfile.id)
        ).all()
    )
    discoveries = list(
        session.scalars(
            select(DiscoveryArticle)
            .options(
                selectinload(DiscoveryArticle.event),
                selectinload(DiscoveryArticle.sources).selectinload(
                    DiscoveryArticleSource.source_record
                ),
                selectinload(DiscoveryArticle.plant_links).selectinload(
                    DiscoveryArticlePlant.plant_profile
                ),
            )
            .order_by(DiscoveryArticle.id)
        ).all()
    )
    materials = list(
        session.scalars(
            select(MaterialStory)
            .options(selectinload(MaterialStory.sources))
            .order_by(MaterialStory.id)
        ).all()
    )
    items = (
        [_plant_item(item) for item in profiles]
        + [_discovery_item(item) for item in discoveries]
        + [_material_item(item) for item in materials]
    )
    normalized_query = (query or "").strip().casefold()
    if normalized_query:
        items = [
            item
            for item in items
            if normalized_query
            in " ".join(
                filter(
                    None,
                    (str(item.id), item.title, item.plant_identity, item.pmid),
                )
            ).casefold()
        ]
    if content_type:
        items = [item for item in items if item.content_type == content_type]
    if editorial_status:
        items = [item for item in items if item.status == editorial_status]
    statuses = sorted({item.status for item in items})
    items.sort(key=lambda item: (item.timestamp, str(item.id)), reverse=True)
    normalized_page, offset, total_pages = _page_bounds(len(items), page, page_size)
    return AdminContentPageResponse(
        summary=_summary(session),
        items=items[offset : offset + page_size],
        total=len(items),
        page=normalized_page,
        page_size=page_size,
        total_pages=total_pages,
        statuses=statuses,
    )


def _source_item(
    record: SourceRecord, source_by_id: dict, content_type: str | None
) -> AdminSourceItemResponse | None:
    associations: dict[tuple[str, str], AdminSourceAssociationResponse] = {}
    roles: set[str] = set()
    for link in record.plant_links:
        roles.add(link.support_role)
        profile = link.plant_profile
        association = AdminSourceAssociationResponse(
            content_id=profile.id,
            content_type="plant_profile",
            title=profile.display_common_name,
            internal_path=f"/plants/{profile.slug}",
        )
        associations[(association.content_type, str(association.content_id))] = (
            association
        )
    for link in record.discovery_article_links:
        roles.add(link.support_role)
        article = link.article
        association = AdminSourceAssociationResponse(
            content_id=article.id,
            content_type="discovery",
            title=article.headline,
            internal_path=f"/discoveries/{article.slug}",
        )
        associations[(association.content_type, str(association.content_id))] = (
            association
        )
    for link in record.material_story_links:
        roles.add(link.support_role)
        story = link.story
        association = AdminSourceAssociationResponse(
            content_id=story.id,
            content_type="material_story",
            title=story.title,
            internal_path=f"/materials-and-craft/{story.slug}",
        )
        associations[(association.content_type, str(association.content_id))] = (
            association
        )
    if content_type and not any(
        association.content_type == content_type
        for association in associations.values()
    ):
        return None
    source = source_by_id.get(record.source_id)
    host = urlparse(record.canonical_url).hostname or ""
    return AdminSourceItemResponse(
        id=record.id,
        source_name=source.name if source else record.publisher,
        source_type=record.source_type,
        authoritative_domain=host.removeprefix("www."),
        external_identifier=record.external_identifier,
        doi=record.doi,
        title=record.title,
        publisher=record.publisher,
        provenance_roles=sorted(roles),
        linked_content_count=len(associations),
        associated_content=sorted(
            associations.values(), key=lambda item: (item.content_type, item.title)
        ),
        created_at=record.collected_at,
        external_url=record.canonical_url,
    )


@router.get(
    "/sources",
    response_model=AdminSourcePageResponse,
    dependencies=[Depends(require_editor)],
)
def source_catalog(
    query: str | None = Query(default=None, max_length=120),
    source_type: str | None = Query(default=None, max_length=100),
    content_type: Literal["plant_profile", "discovery", "material_story"] | None = None,
    page: int = Query(default=1),
    page_size: int = Query(default=12, ge=1, le=50),
    session: Session = Depends(get_session),
) -> AdminSourcePageResponse:
    sources = list(session.scalars(select(Source).order_by(Source.name)).all())
    source_by_id = {source.id: source for source in sources}
    records = list(
        session.scalars(
            select(SourceRecord).options(
                selectinload(SourceRecord.plant_links).selectinload(
                    PlantProfileSource.plant_profile
                ),
                selectinload(SourceRecord.discovery_article_links).selectinload(
                    DiscoveryArticleSource.article
                ),
                selectinload(SourceRecord.material_story_links).selectinload(
                    MaterialStorySource.story
                ),
            )
        ).all()
    )
    all_items = [
        item
        for record in records
        if (item := _source_item(record, source_by_id, content_type)) is not None
    ]
    available_source_types = sorted({item.source_type for item in all_items})
    normalized_query = (query or "").strip().casefold()
    if normalized_query:
        all_items = [
            item
            for item in all_items
            if normalized_query
            in " ".join(
                (
                    str(item.id),
                    item.source_name,
                    item.title,
                    item.publisher,
                    item.external_identifier,
                    item.doi or "",
                    " ".join(entry.title for entry in item.associated_content),
                )
            ).casefold()
        ]
    if source_type:
        all_items = [item for item in all_items if item.source_type == source_type]
    all_items.sort(key=lambda item: (item.source_name, item.title, str(item.id)))
    normalized_page, offset, total_pages = _page_bounds(len(all_items), page, page_size)
    return AdminSourcePageResponse(
        items=all_items[offset : offset + page_size],
        total=len(all_items),
        page=normalized_page,
        page_size=page_size,
        total_pages=total_pages,
        source_count=len(sources),
        source_record_count=len(records),
        source_types=available_source_types,
    )
