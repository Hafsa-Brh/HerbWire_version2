import math

from backend.app.api.discovery_responses import public_discovery_article_response
from backend.app.api.schemas import (
    PublicDiscoveryArticlePageResponse,
    PublicDiscoveryArticleResponse,
)
from backend.app.db.session import get_session
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryArticlePlant,
    DiscoveryArticleSource,
    DiscoveryEvent,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette import status

router = APIRouter(prefix="/discoveries")


def _published_options():
    return (
        selectinload(DiscoveryArticle.event).selectinload(DiscoveryEvent.source_record),
        selectinload(DiscoveryArticle.sources).selectinload(
            DiscoveryArticleSource.source_record
        ),
        selectinload(DiscoveryArticle.reviews),
        selectinload(DiscoveryArticle.plant_links).selectinload(
            DiscoveryArticlePlant.plant_profile
        ),
    )


@router.get("", response_model=PublicDiscoveryArticlePageResponse)
def list_published_discoveries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    session: Session = Depends(get_session),
) -> PublicDiscoveryArticlePageResponse:
    total = (
        session.scalar(
            select(func.count())
            .select_from(DiscoveryArticle)
            .where(
                DiscoveryArticle.status == "published",
                DiscoveryArticle.published_at.is_not(None),
            )
        )
        or 0
    )
    articles = list(
        session.scalars(
            select(DiscoveryArticle)
            .where(
                DiscoveryArticle.status == "published",
                DiscoveryArticle.published_at.is_not(None),
            )
            .options(*_published_options())
            .order_by(DiscoveryArticle.published_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PublicDiscoveryArticlePageResponse(
        items=[public_discovery_article_response(article) for article in articles],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{slug}", response_model=PublicDiscoveryArticleResponse)
def get_published_discovery(
    slug: str, session: Session = Depends(get_session)
) -> PublicDiscoveryArticleResponse:
    article = session.scalar(
        select(DiscoveryArticle)
        .where(
            DiscoveryArticle.slug == slug,
            DiscoveryArticle.status == "published",
            DiscoveryArticle.published_at.is_not(None),
        )
        .options(*_published_options())
    )
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published discovery not found.",
        )
    return public_discovery_article_response(article)
