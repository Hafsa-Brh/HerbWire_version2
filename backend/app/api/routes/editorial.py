from collections import defaultdict
from uuid import UUID

from backend.app.api.routes.plants import plant_detail
from backend.app.api.schemas import (
    AgentMetricResponse,
    AgentPerformanceResponse,
    DecisionRequest,
    PipelineRunResponse,
    PlantRevisionResponse,
    ReviewResponse,
    SeedResponse,
)
from backend.app.core.auth import require_editor_session
from backend.app.db.session import get_session
from backend.app.domains.encyclopedia.service import (
    approve_profile_revision,
    approve_review,
    get_profile_revision,
    get_review,
    hold_profile_revision,
    list_profile_revisions,
    list_reviews,
    promote_profile_revision,
    publish_profile,
    reject_review,
    revision_promotion_eligibility,
    seed_curated_profiles,
)
from backend.app.domains.pipeline.fixture_pipeline import run_fixture_pipeline
from backend.app.models.encyclopedia import (
    PipelineRun,
    PipelineStageResult,
    SourceRecord,
)
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette import status

router = APIRouter(prefix="/admin")


def require_editor(request: Request) -> None:
    require_editor_session(request)


def review_response(review) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        content_type=review.content_type,
        status=review.status,
        reviewer_name=review.reviewer_name,
        decision_reason=review.decision_reason,
        review_payload=review.review_payload,
        created_at=review.created_at,
        decided_at=review.decided_at,
        plant_profile=plant_detail(review.plant_profile)
        if review.plant_profile
        else None,
    )


def revision_response(session: Session, revision) -> PlantRevisionResponse:
    payload = revision.content_payload
    source_ids = [item["source_id"] for item in payload["source_refs"]]
    records = list(
        session.scalars(
            select(SourceRecord).where(SourceRecord.external_identifier.in_(source_ids))
        ).all()
    )
    by_identifier = {record.external_identifier: record for record in records}
    proposed_sources = [
        by_identifier[source_id]
        for source_id in source_ids
        if source_id in by_identifier
    ]
    promotion_eligible, promotion_error_code, promotion_error_message = (
        revision_promotion_eligibility(session, revision)
    )
    return PlantRevisionResponse(
        id=revision.id,
        plant_profile_id=revision.plant_profile_id,
        slug=revision.plant_profile.slug,
        display_common_name=revision.plant_profile.display_common_name,
        current_version=revision.plant_profile.version,
        proposed_version=revision.version,
        status=revision.status,
        promotion_eligible=promotion_eligible,
        promotion_error_code=promotion_error_code,
        promotion_error_message=promotion_error_message,
        content_checksum=revision.content_checksum,
        current_content=plant_detail(revision.plant_profile),
        proposed_content=payload["profile"],
        proposed_sources=[
            {
                "id": record.id,
                "external_identifier": record.external_identifier,
                "url": record.url,
                "canonical_url": record.canonical_url,
                "title": record.title,
                "publisher": record.publisher,
                "source_type": record.source_type,
                "original_language": record.original_language,
                "license_status": record.license_status,
                "supports": record.supports,
                "accessed_at": record.collected_at,
            }
            for record in proposed_sources
        ],
        reviewer_name=revision.reviewer_name,
        decision_reason=revision.decision_reason,
        created_at=revision.created_at,
        reviewed_at=revision.reviewed_at,
        promoted_at=revision.promoted_at,
    )


@router.post(
    "/dev/seed-curated",
    response_model=SeedResponse,
    dependencies=[Depends(require_editor)],
)
def seed_curated(session: Session = Depends(get_session)) -> SeedResponse:
    return SeedResponse(**seed_curated_profiles(session))


@router.get(
    "/reviews",
    response_model=list[ReviewResponse],
    dependencies=[Depends(require_editor)],
)
def read_reviews(session: Session = Depends(get_session)) -> list[ReviewResponse]:
    return [review_response(review) for review in list_reviews(session)]


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    dependencies=[Depends(require_editor)],
)
def read_review(
    review_id: UUID, session: Session = Depends(get_session)
) -> ReviewResponse:
    return review_response(get_review(session, review_id))


@router.post(
    "/reviews/{review_id}/approve",
    response_model=ReviewResponse,
    dependencies=[Depends(require_editor)],
)
def approve(
    review_id: UUID, request: DecisionRequest, session: Session = Depends(get_session)
) -> ReviewResponse:
    return review_response(approve_review(session, review_id, request.reviewer_name))


@router.post(
    "/reviews/{review_id}/reject",
    response_model=ReviewResponse,
    dependencies=[Depends(require_editor)],
)
def reject(
    review_id: UUID, request: DecisionRequest, session: Session = Depends(get_session)
) -> ReviewResponse:
    return review_response(
        reject_review(session, review_id, request.reason or "", request.reviewer_name)
    )


@router.post("/plants/{plant_id}/publish", dependencies=[Depends(require_editor)])
def publish(plant_id: UUID, session: Session = Depends(get_session)):
    return plant_detail(publish_profile(session, plant_id))


@router.get(
    "/revisions",
    response_model=list[PlantRevisionResponse],
    dependencies=[Depends(require_editor)],
)
def read_revisions(
    session: Session = Depends(get_session),
) -> list[PlantRevisionResponse]:
    return [
        revision_response(session, item) for item in list_profile_revisions(session)
    ]


@router.get(
    "/revisions/{revision_id}",
    response_model=PlantRevisionResponse,
    dependencies=[Depends(require_editor)],
)
def read_revision(
    revision_id: UUID, session: Session = Depends(get_session)
) -> PlantRevisionResponse:
    return revision_response(session, get_profile_revision(session, revision_id))


@router.post(
    "/revisions/{revision_id}/approve",
    response_model=PlantRevisionResponse,
    dependencies=[Depends(require_editor)],
)
def approve_revision(
    revision_id: UUID,
    request: DecisionRequest,
    session: Session = Depends(get_session),
) -> PlantRevisionResponse:
    return revision_response(
        session,
        approve_profile_revision(session, revision_id, request.reviewer_name),
    )


@router.post(
    "/revisions/{revision_id}/reject",
    response_model=PlantRevisionResponse,
    dependencies=[Depends(require_editor)],
)
def reject_revision(
    revision_id: UUID,
    request: DecisionRequest,
    session: Session = Depends(get_session),
) -> PlantRevisionResponse:
    return revision_response(
        session,
        hold_profile_revision(
            session, revision_id, request.reason or "", request.reviewer_name
        ),
    )


@router.post(
    "/revisions/{revision_id}/promote",
    response_model=PlantRevisionResponse,
    dependencies=[Depends(require_editor)],
)
def promote_revision(
    revision_id: UUID, session: Session = Depends(get_session)
) -> PlantRevisionResponse:
    return revision_response(session, promote_profile_revision(session, revision_id))


@router.post(
    "/dev/run-discovery-fixture",
    response_model=PipelineRunResponse,
    dependencies=[Depends(require_editor)],
)
def run_discovery_fixture(session: Session = Depends(get_session)) -> PipelineRun:
    return run_fixture_pipeline(session)


@router.get(
    "/pipeline/runs",
    response_model=list[PipelineRunResponse],
    dependencies=[Depends(require_editor)],
)
def read_pipeline_runs(session: Session = Depends(get_session)) -> list[PipelineRun]:
    return list(
        session.scalars(
            select(PipelineRun)
            .options(selectinload(PipelineRun.stages))
            .order_by(PipelineRun.started_at.desc())
        ).all()
    )


@router.get(
    "/pipeline/runs/{run_id}",
    response_model=PipelineRunResponse,
    dependencies=[Depends(require_editor)],
)
def read_pipeline_run(
    run_id: UUID, session: Session = Depends(get_session)
) -> PipelineRun:
    run = session.scalar(
        select(PipelineRun)
        .where(PipelineRun.id == run_id)
        .options(selectinload(PipelineRun.stages))
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found."
        )
    return run


@router.get(
    "/agent-performance",
    response_model=AgentPerformanceResponse,
    dependencies=[Depends(require_editor)],
)
def read_agent_performance(
    session: Session = Depends(get_session),
) -> AgentPerformanceResponse:
    runs = list(session.scalars(select(PipelineRun)).all())
    stages = list(
        session.scalars(
            select(PipelineStageResult).order_by(PipelineStageResult.created_at.desc())
        ).all()
    )
    grouped = defaultdict(list)
    for stage in stages:
        grouped[stage.name].append(stage)

    metrics: list[AgentMetricResponse] = []
    for name, items in sorted(grouped.items()):
        durations = [item.duration_ms for item in items]
        completed = [item for item in items if item.status == "succeeded"]
        metrics.append(
            AgentMetricResponse(
                name=name,
                total_runs=len(items),
                succeeded=sum(item.status == "succeeded" for item in items),
                failed=sum(item.status == "failed" for item in items),
                held=sum(item.status == "held" for item in items),
                skipped=sum(item.status == "skipped" for item in items),
                average_duration_ms=(
                    round(sum(durations) / len(durations)) if durations else 0
                ),
                last_status=items[0].status if items else None,
                last_completed_at=completed[0].created_at if completed else None,
            )
        )

    return AgentPerformanceResponse(
        total_runs=len(runs),
        succeeded_runs=sum(run.status == "succeeded" for run in runs),
        failed_runs=sum(run.status == "failed" for run in runs),
        held_runs=sum(run.status == "held" for run in runs),
        auto_published=0,
        last_execution=max((run.started_at for run in runs), default=None),
        stages=metrics,
    )
