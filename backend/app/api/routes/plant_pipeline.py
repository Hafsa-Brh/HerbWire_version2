"""Authenticated Editorial Desk API for the sequential Plant pipeline."""

from uuid import UUID

from backend.app.api.plant_pipeline_schemas import (
    PlantPipelineItemResponse,
    PlantPipelinePreviewResponse,
    PlantPipelineRunResponse,
    PlantPipelineStartRequest,
)
from backend.app.core.auth import require_editor_session
from backend.app.db.session import get_session
from backend.app.domains.encyclopedia.plant_eligibility import active_pipeline_domain
from backend.app.domains.pipeline.plant_profile_pipeline import (
    PlantPipelineBusyError,
    PlantPipelineStateError,
    advance_run,
    execute_run_to_terminal,
    get_current_run,
    get_run,
    preview_candidates,
    retry_run,
    start_run,
)
from backend.app.models.encyclopedia import PipelineRun
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette import status

router = APIRouter(prefix="/admin/plant-pipeline")


def require_editor(request: Request) -> None:
    require_editor_session(request)


def _response(run: PipelineRun) -> PlantPipelineRunResponse:
    items = [
        PlantPipelineItemResponse(
            id=item.id,
            title=item.plant_profile.display_common_name,
            status=item.status,
            editorial_status=item.plant_profile.status,
            plant_profile_id=item.plant_profile_id,
            review_id=item.review_id,
        )
        for item in sorted(run.plant_items, key=lambda value: value.position)
        if item.plant_profile is not None
    ]
    return PlantPipelineRunResponse(id=run.id, status=run.status, items=items)


@router.get(
    "/preview",
    response_model=PlantPipelinePreviewResponse,
    dependencies=[Depends(require_editor)],
)
def preview(
    count: int = Query(default=1, ge=1, le=10),
    all_available: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> PlantPipelinePreviewResponse:
    details = preview_candidates(session, count, all_available=all_available)
    active = active_pipeline_domain(session)
    can_start = bool(details["can_start"]) and active is None
    reason = (
        "An editorial generation pipeline is currently active."
        if active is not None
        else details["unavailable_reason"]
    )
    return PlantPipelinePreviewResponse(
        can_start=can_start,
        unavailable_reason=None if can_start else reason,
        active_pipeline=active,
    )


@router.get(
    "/runs/current",
    response_model=PlantPipelineRunResponse | None,
    dependencies=[Depends(require_editor)],
)
def current(session: Session = Depends(get_session)):
    run = get_current_run(session)
    return _response(run) if run is not None else None


@router.get(
    "/runs/{run_id}",
    response_model=PlantPipelineRunResponse,
    dependencies=[Depends(require_editor)],
)
def read(run_id: UUID, session: Session = Depends(get_session)):
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Plant pipeline run not found.")
    return _response(run)


@router.post(
    "/runs",
    response_model=PlantPipelineRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_editor)],
)
def start(
    payload: PlantPipelineStartRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    try:
        run = start_run(
            session,
            payload.count,
            payload.idempotency_key,
            all_available=payload.all_available,
        )
        if run.status == "running":
            background_tasks.add_task(execute_run_to_terminal, run.id)
        return _response(run)
    except PlantPipelineBusyError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/runs/{run_id}/advance",
    response_model=PlantPipelineRunResponse,
    dependencies=[Depends(require_editor)],
)
def advance(run_id: UUID, session: Session = Depends(get_session)):
    try:
        return _response(advance_run(session, run_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PlantPipelineStateError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/runs/{run_id}/retry",
    response_model=PlantPipelineRunResponse,
    dependencies=[Depends(require_editor)],
)
def retry(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    try:
        run = retry_run(session, run_id)
        background_tasks.add_task(execute_run_to_terminal, run.id)
        return _response(run)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PlantPipelineStateError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
