from backend.app.api.discovery_responses import public_discovery_article_response
from backend.app.api.schemas import (
    DiscoveryFilterOption,
    PublicDiscoveryArticlePageResponse,
    PublicDiscoveryArticleResponse,
    PublicDiscoveryFilters,
)
from backend.app.db.session import get_session
from backend.app.domains.discovery.service import (
    discovery_article_load_options,
    list_published_discovery_articles,
)
from backend.app.models.encyclopedia import DiscoveryArticle
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette import status

router = APIRouter(prefix="/discoveries")


def _filter_options(session: Session) -> PublicDiscoveryFilters:
    articles = list(
        session.scalars(
            select(DiscoveryArticle)
            .where(
                DiscoveryArticle.status == "published",
                DiscoveryArticle.published_at.is_not(None),
            )
            .options(*discovery_article_load_options())
        ).all()
    )
    plants: dict[str, str] = {}
    study_types: set[str] = set()
    strengths: set[str] = set()
    years: set[str] = set()
    countries: dict[str, str] = {}
    for article in articles:
        for link in article.plant_links:
            plants[link.plant_profile.display_common_name] = (
                f"{link.plant_profile.display_common_name} "
                f"({link.plant_profile.accepted_scientific_name})"
            )
        identity = article.event.evidence_package.get("botanical_identity") or {}
        if identity.get("common_name"):
            plants[identity["common_name"]] = (
                f"{identity['common_name']} "
                f"({identity.get('accepted_scientific_name', 'identity verified')})"
            )
        if article.article_type:
            study_types.add(article.article_type)
        if article.evidence_strength:
            strengths.add(article.evidence_strength)
        publication_date = article.event.source_record.source_publication_date
        if publication_date and len(publication_date) >= 4:
            years.add(publication_date[:4])
        for geography in article.geography:
            if (
                geography.get("geography_kind", "research_geography")
                != "research_geography"
            ):
                continue
            code = geography.get("iso_country_code")
            if code:
                countries[code.upper()] = geography.get("display_label") or code.upper()
            for item in geography.get("iso_country_codes") or []:
                countries[item.upper()] = item.upper()

    def option(value: str, label: str | None = None) -> DiscoveryFilterOption:
        return DiscoveryFilterOption(value=value, label=label or value)

    return PublicDiscoveryFilters(
        plants=[option(value, plants[value]) for value in sorted(plants)],
        study_types=[option(value) for value in sorted(study_types)],
        evidence_strengths=[option(value) for value in sorted(strengths)],
        publication_years=[option(value) for value in sorted(years, reverse=True)],
        research_countries=[
            option(value, countries[value]) for value in sorted(countries)
        ],
    )


@router.get("", response_model=PublicDiscoveryArticlePageResponse)
def list_published_discoveries(
    query: str | None = Query(default=None, max_length=120),
    plant: str | None = Query(default=None, max_length=255),
    study_type: str | None = Query(default=None, max_length=100),
    evidence_strength: str | None = Query(default=None, max_length=50),
    publication_year: int | None = Query(default=None, ge=1900, le=2100),
    research_country: str | None = Query(default=None, min_length=2, max_length=2),
    page: int = Query(default=1),
    page_size: int = Query(default=12, ge=1, le=50),
    session: Session = Depends(get_session),
) -> PublicDiscoveryArticlePageResponse:
    articles, total, normalized_page = list_published_discovery_articles(
        session,
        query=query,
        plant=plant,
        study_type=study_type,
        evidence_strength=evidence_strength,
        publication_year=publication_year,
        research_country=research_country,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PublicDiscoveryArticlePageResponse(
        items=[public_discovery_article_response(article) for article in articles],
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=total_pages,
        total_pages=total_pages,
        filters=_filter_options(session),
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
        .options(*discovery_article_load_options())
    )
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published discovery not found.",
        )
    return public_discovery_article_response(article)
