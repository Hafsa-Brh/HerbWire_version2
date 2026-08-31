from collections import defaultdict
from uuid import UUID

from backend.app.api.routes.plants import plant_detail
from backend.app.api.schemas import (
    AgentMetricResponse,
    AgentPerformanceResponse,
    DecisionRequest,
    PipelineRunResponse,
    ReviewResponse,
    SeedResponse,
)
from backend.app.core.auth import require_editor_session
from backend.app.db.session import get_session
from backend.app.domains.encyclopedia.service import (
    approve_review,
    get_review,
    list_reviews,
    publish_profile,
    reject_review,
    seed_curated_profiles,
)
from backend.app.domains.pipeline.fixture_pipeline import run_fixture_pipeline
from backend.app.models.encyclopedia import PipelineRun, PipelineStageResult
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
