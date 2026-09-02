import math
from uuid import UUID

from backend.app.api.discovery_responses import discovery_article_response
from backend.app.api.schemas import (
    DecisionRequest,
    DiscoveryArticlePageResponse,
    DiscoveryArticleResponse,
    DiscoveryRunRequest,
    PipelineRunResponse,
)
from backend.app.collectors.providers.base import CollectionProvider, CollectionRequest
from backend.app.collectors.providers.pubmed import (
    PubMedCollectionProvider,
    PubMedProviderConfig,
)
from backend.app.core.auth import require_editor_session
from backend.app.core.settings import get_settings
from backend.app.db.session import get_session
from backend.app.domains.discovery.service import (
    decide_discovery_article,
    get_discovery_article,
    list_discovery_articles,
    run_discovery_pipeline,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette import status

router = APIRouter(prefix="/admin/discovery")


def require_editor(request: Request) -> None:
    require_editor_session(request)


def get_pubmed_provider() -> CollectionProvider:
    settings = get_settings()
    try:
        return PubMedCollectionProvider(
            PubMedProviderConfig(
                email=settings.ncbi_email or "",
                timeout_seconds=settings.ncbi_request_timeout_seconds,
                max_retries=settings.ncbi_max_retries,
            )
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PubMed collection is not configured for an explicit live run.",
        ) from error


@router.post(
    "/runs",
    response_model=PipelineRunResponse,
    dependencies=[Depends(require_editor)],
)
def trigger_pubmed_run(
    payload: DiscoveryRunRequest,
    session: Session = Depends(get_session),
    provider: CollectionProvider = Depends(get_pubmed_provider),
) -> PipelineRunResponse:
    request = CollectionRequest(
        start_date=payload.start_date,
        end_date=payload.end_date,
        max_records=payload.max_records,
        date_type=payload.date_type,
    )
    return PipelineRunResponse.model_validate(
        run_discovery_pipeline(session, request, provider)
    )


@router.get(
    "/reviews",
    response_model=DiscoveryArticlePageResponse,
    dependencies=[Depends(require_editor)],
)
def read_discovery_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> DiscoveryArticlePageResponse:
    articles = list_discovery_articles(session)
    total = len(articles)
    selected = articles[(page - 1) * page_size : page * page_size]
    return DiscoveryArticlePageResponse(
        items=[discovery_article_response(article) for article in selected],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get(
    "/reviews/{article_id}",
    response_model=DiscoveryArticleResponse,
    dependencies=[Depends(require_editor)],
)
def read_discovery_review(
    article_id: UUID, session: Session = Depends(get_session)
) -> DiscoveryArticleResponse:
    article = get_discovery_article(session, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Discovery article not found.")
    return discovery_article_response(article)


def _decision(
    article_id: UUID,
    action: str,
    payload: DecisionRequest,
    session: Session,
) -> DiscoveryArticleResponse:
    try:
        article = decide_discovery_article(
            session,
            article_id,
            action,
            payload.reviewer_name,
            payload.reason,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return discovery_article_response(article)


@router.post(
    "/reviews/{article_id}/approve",
    response_model=DiscoveryArticleResponse,
    dependencies=[Depends(require_editor)],
)
def approve_discovery(
    article_id: UUID,
    payload: DecisionRequest,
    session: Session = Depends(get_session),
) -> DiscoveryArticleResponse:
    return _decision(article_id, "approved", payload, session)


@router.post(
    "/reviews/{article_id}/hold",
    response_model=DiscoveryArticleResponse,
    dependencies=[Depends(require_editor)],
)
def hold_discovery(
    article_id: UUID,
    payload: DecisionRequest,
    session: Session = Depends(get_session),
) -> DiscoveryArticleResponse:
    return _decision(article_id, "held", payload, session)


@router.post(
    "/reviews/{article_id}/reject",
    response_model=DiscoveryArticleResponse,
    dependencies=[Depends(require_editor)],
)
def reject_discovery(
    article_id: UUID,
    payload: DecisionRequest,
    session: Session = Depends(get_session),
) -> DiscoveryArticleResponse:
    return _decision(article_id, "rejected", payload, session)
