from math import ceil

from backend.app.api.material_schemas import (
    MaterialStoryDetailResponse,
    MaterialStoryPageResponse,
)
from backend.app.db.session import get_session
from backend.app.models.materials import MaterialStory, MaterialStorySource
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

router = APIRouter(prefix="/materials")


def _summary(story: MaterialStory) -> dict:
    return {
        "id": story.id,
        "slug": story.slug,
        "title": story.title,
        "deck": story.deck,
        "category": story.category,
        "material_labels": story.material_labels,
        "geography_label": story.geography_label,
        "reading_time_minutes": story.reading_time_minutes,
        "featured": story.featured,
        "published_at": story.published_at,
        "hero_media": story.hero_media,
    }


@router.get("", response_model=MaterialStoryPageResponse)
def list_materials(
    category: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    session: Session = Depends(get_session),
) -> MaterialStoryPageResponse:
    base = select(MaterialStory).where(MaterialStory.status == "published")
    count = (
        select(func.count())
        .select_from(MaterialStory)
        .where(MaterialStory.status == "published")
    )
    if category:
        base = base.where(MaterialStory.category == category)
        count = count.where(MaterialStory.category == category)
    total = session.scalar(count) or 0
    total_pages = max(1, ceil(total / page_size))
    normalized_page = min(page, total_pages)
    stories = session.scalars(
        base.order_by(
            MaterialStory.featured.desc(),
            MaterialStory.published_at.desc(),
            MaterialStory.sort_order,
            MaterialStory.id,
        )
        .offset((normalized_page - 1) * page_size)
        .limit(page_size)
    ).all()
    categories = list(
        session.scalars(
            select(MaterialStory.category)
            .where(MaterialStory.status == "published")
            .distinct()
            .order_by(MaterialStory.category)
        ).all()
    )
    return MaterialStoryPageResponse(
        items=[_summary(story) for story in stories],
        total=total,
        page=normalized_page,
        page_size=page_size,
        total_pages=total_pages,
        categories=categories,
    )


@router.get("/{slug}", response_model=MaterialStoryDetailResponse)
def material_detail(
    slug: str, session: Session = Depends(get_session)
) -> MaterialStoryDetailResponse:
    story = session.scalar(
        select(MaterialStory)
        .where(MaterialStory.slug == slug, MaterialStory.status == "published")
        .options(
            selectinload(MaterialStory.sources).selectinload(
                MaterialStorySource.source_record
            )
        )
    )
    if story is None:
        raise HTTPException(status_code=404, detail="Material story not found")
    sources = [
        {
            "id": link.source_record.id,
            "source_name": link.source_record.publisher,
            "title": link.source_record.title,
            "source_type": link.source_record.source_type,
            "external_identifier": link.source_record.external_identifier,
            "canonical_url": link.source_record.canonical_url,
            "supported_sections": link.supported_sections,
        }
        for link in story.sources
    ]
    related_rows = session.scalars(
        select(MaterialStory)
        .where(MaterialStory.status == "published", MaterialStory.id != story.id)
        .order_by(
            (MaterialStory.category == story.category).desc(),
            MaterialStory.sort_order,
            MaterialStory.id,
        )
        .limit(3)
    ).all()
    return MaterialStoryDetailResponse(
        **_summary(story),
        content_version=story.content_version,
        sections=story.sections,
        sources=sources,
        related=[_summary(item) for item in related_rows],
    )
