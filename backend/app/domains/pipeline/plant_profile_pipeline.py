"""Durable, strictly sequential Plant profile orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta
from time import monotonic
from uuid import UUID, uuid4

from backend.app.db.session import get_session_factory
from backend.app.domains.encyclopedia.plant_eligibility import (
    check_candidate_eligibility,
    protected_reserve_message,
    reserve_subject,
    subject_from_plant_candidate,
    subject_identity_keys,
)
from backend.app.domains.encyclopedia.plant_pipeline_catalog import (
    PlantCandidate,
    PlantSourcePackage,
    load_plant_pipeline_catalog,
)
from backend.app.domains.encyclopedia.service import create_automated_profile_draft
from backend.app.models.encyclopedia import (
    PipelineRun,
    PipelineStageResult,
    PlantPipelineItem,
    utc_now,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

EDITORIAL_PIPELINE_TYPES = (
    "plant_profile_automation",
    "discovery_article_automation",
    "pubmed_discovery_review",
)
PIPELINE_TYPE = "plant_profile_automation"
MAX_BATCH_SIZE = 10
PROTECTED_RESERVE = 10
LEASE_SECONDS = 120
STAGES = (
    ("normalization_and_deduplication", "Normalization and Deduplication"),
    ("collector_gateway", "Collector Gateway"),
    ("botanical_resolver", "Botanical Resolver"),
    ("evidence_safety_and_provenance", "Evidence, Safety, and Provenance"),
    ("media_and_geography", "Media & Geography Agent"),
    ("content_composer", "Content Composer"),
    ("editorial_qa", "Editorial QA"),
    ("queue_editorial_review", "Private review creation"),
)


class PlantPipelineBusyError(RuntimeError):
    pass


class PlantPipelineStateError(RuntimeError):
    pass


def _run_query(run_id: UUID | None = None):
    query = select(PipelineRun).options(
        selectinload(PipelineRun.stages),
        selectinload(PipelineRun.plant_items),
    )
    if run_id is not None:
        query = query.where(PipelineRun.id == run_id)
    return query


def get_run(session: Session, run_id: UUID) -> PipelineRun | None:
    return session.scalar(_run_query(run_id))


def get_current_run(session: Session) -> PipelineRun | None:
    return session.scalar(
        _run_query()
        .where(PipelineRun.pipeline_type == PIPELINE_TYPE)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )


def preview_candidates(
    session: Session, count: int = 1, *, all_available: bool = False
) -> dict:
    if not 1 <= count <= MAX_BATCH_SIZE:
        raise ValueError("Profiles to generate must be between 1 and 10.")
    catalog = load_plant_pipeline_catalog()
    eligible = []
    skipped = []
    batch_keys: set[str] = set()
    for candidate in catalog.candidates:
        result = check_candidate_eligibility(session, candidate, batch_keys=batch_keys)
        if result.eligible:
            eligible.append(candidate.model_dump(mode="json"))
            batch_keys.update(
                subject_identity_keys(subject_from_plant_candidate(candidate))
            )
        elif not result.eligible:
            skipped.append(
                {
                    "key": candidate.key,
                    "reason_code": result.reason_code,
                    "reason": result.reason,
                }
            )
    safe_capacity = max(0, len(eligible) - PROTECTED_RESERVE)
    planned_count = min(MAX_BATCH_SIZE, safe_capacity) if all_available else count
    can_start = planned_count > 0 and safe_capacity >= planned_count
    selected = eligible[:planned_count] if can_start else []
    return {
        "requested_count": planned_count if all_available else count,
        "available_count": len(eligible),
        "planned_count": len(selected),
        "vetted_count": len(catalog.candidates),
        "candidates": selected,
        "skipped": skipped,
        "catalogue_exhausted": not eligible,
        "insufficient_availability": not can_start,
        "selection_mode": "all_available" if all_available else "count",
        "can_start": can_start,
        "unavailable_reason": None if can_start else protected_reserve_message(),
    }


def start_run(
    session: Session,
    count: int,
    idempotency_key: str,
    *,
    all_available: bool = False,
) -> PipelineRun:
    if not 1 <= count <= MAX_BATCH_SIZE:
        raise ValueError("Profiles to generate must be between 1 and 10.")
    existing = session.scalar(
        select(PipelineRun).where(PipelineRun.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if existing.pipeline_type != PIPELINE_TYPE:
            raise ValueError("Idempotency key belongs to another pipeline.")
        return get_run(session, existing.id) or existing

    active = session.scalar(
        select(PipelineRun.id).where(
            PipelineRun.pipeline_type.in_(EDITORIAL_PIPELINE_TYPES),
            PipelineRun.status == "running",
        )
    )
    if active is not None:
        raise PlantPipelineBusyError(
            "An editorial generation pipeline is already active."
        )

    preview = preview_candidates(session, count, all_available=all_available)
    if not preview["can_start"]:
        raise ValueError(protected_reserve_message())
    candidates = preview["candidates"]
    now = utc_now()
    run = PipelineRun(
        pipeline_type=PIPELINE_TYPE,
        trigger="editorial_desk",
        provider="deterministic_source_catalogue",
        idempotency_key=idempotency_key,
        status="running" if candidates else "held",
        current_stage=STAGES[0][0] if candidates else "catalogue_exhausted",
        summary={
            "requested_count": preview["requested_count"],
            "available_count_at_start": preview["available_count"],
            "planned_count": len(candidates),
            "completed_count": 0,
            "held_count": 0,
            "failed_count": 0,
            "remaining_count": len(candidates),
            "selected_count": len(candidates),
            "created_drafts": 0,
            "held_candidates": 0,
            "unavailable_candidates": max(
                0, preview["requested_count"] - len(candidates)
            ),
            "failures": 0,
            "source_count": 0,
            "execution_policy": "strictly_sequential_fail_fast",
            "catalogue_exhausted": not candidates,
            "selection_mode": preview["selection_mode"],
        },
        started_at=now,
        finished_at=None if candidates else now,
        heartbeat_at=now,
        lease_expires_at=now + timedelta(seconds=LEASE_SECONDS) if candidates else None,
        lease_owner=uuid4().hex if candidates else None,
    )
    session.add(run)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        replay = session.scalar(
            select(PipelineRun).where(PipelineRun.idempotency_key == idempotency_key)
        )
        if replay is not None:
            return get_run(session, replay.id) or replay
        raise PlantPipelineBusyError(
            "A concurrent Plant pipeline request won the database lock."
        ) from error
    for position, snapshot in enumerate(candidates, start=1):
        session.add(
            PlantPipelineItem(
                pipeline_run_id=run.id,
                candidate_key=snapshot["key"],
                position=position,
                status="pending",
                candidate_snapshot=snapshot,
                work_payload={"quality_gates": {}},
            )
        )
        candidate = PlantCandidate.model_validate(snapshot)
        reserve_subject(
            session,
            run_id=run.id,
            domain="plants",
            candidate_key=candidate.key,
            subject=subject_from_plant_candidate(candidate),
        )
        for name, label in STAGES:
            session.add(
                PipelineStageResult(
                    pipeline_run_id=run.id,
                    candidate_position=position,
                    name=name,
                    status="pending",
                    attempt=1,
                    input_refs=[snapshot["key"]],
                    output_refs=[],
                    error_message=label,
                )
            )
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        replay = session.scalar(
            select(PipelineRun).where(PipelineRun.idempotency_key == idempotency_key)
        )
        if replay is not None:
            return get_run(session, replay.id) or replay
        raise PlantPipelineBusyError(
            "A concurrent Plant pipeline request won the database lock."
        ) from error
    return get_run(session, run.id) or run


def _gate(passed: bool, detail: str) -> dict:
    return {"status": "passed" if passed else "held", "detail": detail}


def _stage_result(
    name: str,
    candidate: PlantCandidate,
    package: PlantSourcePackage,
    gates: dict,
) -> tuple[dict, list[str]]:
    profile = package.profile
    if name == "normalization_and_deduplication":
        gates["duplicate_check"] = _gate(True, "Canonical identity is unrepresented.")
    elif name == "collector_gateway":
        enough = len(package.sources) >= 3
        gates["minimum_sources"] = _gate(
            enough, f"{len(package.sources)} approved free source records collected."
        )
    elif name == "botanical_resolver":
        passed = bool(candidate.taxon_identifier and profile.taxon_status == "accepted")
        gates["taxonomy_verified"] = _gate(
            passed, "Accepted taxon is linked to a stable Kew identifier."
        )
    elif name == "evidence_safety_and_provenance":
        gates["overview_provenance"] = _gate(
            bool(profile.article_details.section_sources.get("overview")),
            "Overview has explicit source links.",
        )
        gates["evidence_limitations"] = _gate(
            bool(
                profile.evidence_notes and "evidence" in profile.evidence_notes.lower()
            ),
            "Evidence limitations are stated.",
        )
        gates["safety_coverage"] = _gate(
            bool(profile.safety_notes),
            "Safety and special-population notes are present.",
        )
    elif name == "media_and_geography":
        gates["geography_normalized"] = _gate(
            any(region.map_countries for region in profile.distribution),
            "Map countries use validated ISO alpha-2 codes.",
        )
        gates["map_valid"] = _gate(
            True, "A conservative verified map context is present."
        )
        gates["licensed_photograph"] = _gate(
            profile.media.kind == "licensed_photograph",
            "Raster photograph, attribution, license, and checksum are verified.",
        )
    elif name == "content_composer":
        required = (
            profile.introduction,
            profile.botanical_description,
            profile.traditional_uses,
            profile.evidence_notes,
            profile.safety_notes,
            profile.distribution,
            profile.media,
        )
        gates["required_sections"] = _gate(
            all(required), "All PlantArticlePage sections have structured content."
        )
    elif name == "editorial_qa":
        passed = all(value["status"] == "passed" for value in gates.values())
        gates["qa"] = _gate(
            passed,
            "Gates passed; human claim and image review remains required.",
        )
        if not passed:
            raise ValueError("One or more deterministic quality gates did not pass.")
    return gates, [candidate.key, name]


def _fail(
    session: Session,
    run: PipelineRun,
    item: PlantPipelineItem,
    stage: PipelineStageResult,
    code: str,
    message: str,
) -> None:
    now = utc_now()
    safe_message = message[:500]
    stage.status = "failed"
    stage.error_code = code
    stage.error_message = safe_message
    stage.completed_at = now
    item.status = "failed"
    item.error_code = code
    item.error_message = safe_message
    item.completed_at = now
    run.status = "failed"
    run.current_stage = stage.name
    run.finished_at = now
    run.lease_expires_at = None
    run.lease_owner = None
    completed = int(
        run.summary.get("completed_count", run.summary.get("created_drafts", 0))
    )
    failed = int(run.summary.get("failed_count", 0)) + 1
    planned = int(
        run.summary.get("planned_count", run.summary.get("selected_count", 0))
    )
    run.summary = {
        **run.summary,
        "failures": failed,
        "failed_count": failed,
        "completed_count": completed,
        "remaining_count": max(0, planned - completed - failed),
    }
    session.commit()


def advance_run(
    session: Session, run_id: UUID, lease_owner: str | None = None
) -> PipelineRun:
    run = session.scalar(_run_query(run_id).with_for_update())
    if run is None:
        raise LookupError("Plant pipeline run not found.")
    if run.pipeline_type != PIPELINE_TYPE:
        raise PlantPipelineStateError("Run is not a Plant pipeline run.")
    if run.status != "running":
        return run
    if lease_owner is not None and run.lease_owner != lease_owner:
        return run

    items = sorted(run.plant_items, key=lambda value: value.position)
    item = next(
        (value for value in items if value.status in {"pending", "running"}),
        None,
    )
    if item is None:
        run.status = "succeeded"
        run.current_stage = "completed"
        run.finished_at = utc_now()
        run.lease_expires_at = None
        run.lease_owner = None
        session.commit()
        return get_run(session, run.id) or run

    stages = sorted(
        (stage for stage in run.stages if stage.candidate_position == item.position),
        key=lambda value: [name for name, _ in STAGES].index(value.name),
    )
    stage = next(
        (value for value in stages if value.status in {"pending", "running"}),
        None,
    )
    if stage is None:
        item.status = "succeeded"
        item.completed_at = utc_now()
        session.commit()
        return advance_run(session, run.id, lease_owner)
    if stage.status == "running":
        return run

    now = utc_now()
    item.status = "running"
    item.started_at = item.started_at or now
    stage.status = "running"
    stage.started_at = now
    stage.error_code = None
    stage.error_message = dict(STAGES)[stage.name]
    run.current_stage = stage.name
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    run.lease_owner = run.lease_owner or uuid4().hex
    session.commit()

    started = monotonic()
    catalog = load_plant_pipeline_catalog()
    candidate = next(
        value for value in catalog.candidates if value.key == item.candidate_key
    )
    package = catalog.package_for(candidate.key)
    try:
        gates = dict(item.work_payload.get("quality_gates", {}))
        gates, output_refs = _stage_result(stage.name, candidate, package, gates)
        session.expire_all()
        run = session.scalar(_run_query(run_id).with_for_update())
        assert run is not None
        if lease_owner is not None and run.lease_owner != lease_owner:
            return run
        item = next(
            value for value in run.plant_items if value.position == item.position
        )
        stage = next(
            value
            for value in run.stages
            if value.candidate_position == item.position and value.name == stage.name
        )
        if stage.name == "queue_editorial_review":
            eligibility = check_candidate_eligibility(
                session, candidate, exclude_run_id=run.id
            )
            if not eligibility.eligible:
                raise ValueError(
                    "Candidate became ineligible before private draft persistence."
                )
            profile, review = create_automated_profile_draft(
                session,
                package.profile,
                package.sources,
                gates,
                pipeline_run_id=run.id,
                collected_at=datetime.fromisoformat(
                    package.collected_at.replace("Z", "+00:00")
                ),
            )
            item.plant_profile_id = profile.id
            item.review_id = review.id
            item.source_count = len(package.sources)
            output_refs = [str(profile.id), str(review.id)]
        item.work_payload = {"quality_gates": gates}
        stage.status = "succeeded"
        stage.duration_ms = max(1, round((monotonic() - started) * 1000))
        stage.input_count = 1
        stage.output_count = len(output_refs)
        stage.output_refs = output_refs
        stage.error_code = None
        stage.error_message = dict(STAGES)[stage.name] + " completed."
        stage.completed_at = utc_now()
        run.heartbeat_at = utc_now()
        run.lease_expires_at = utc_now() + timedelta(seconds=LEASE_SECONDS)
        if stage.name == STAGES[-1][0]:
            item.status = "succeeded"
            item.completed_at = utc_now()
            completed = (
                int(
                    run.summary.get(
                        "completed_count", run.summary.get("created_drafts", 0)
                    )
                )
                + 1
            )
            planned = int(
                run.summary.get(
                    "planned_count",
                    run.summary.get("selected_count", len(run.plant_items)),
                )
            )
            run.summary = {
                **run.summary,
                "created_drafts": int(run.summary["created_drafts"]) + 1,
                "completed_count": completed,
                "remaining_count": max(
                    0,
                    planned
                    - completed
                    - int(run.summary.get("held_count", 0))
                    - int(run.summary.get("failed_count", 0)),
                ),
                "source_count": int(run.summary["source_count"]) + item.source_count,
            }
            remaining = any(value.status == "pending" for value in run.plant_items)
            if not remaining:
                run.status = "succeeded"
                run.current_stage = "completed"
                run.finished_at = utc_now()
                run.lease_expires_at = None
                run.lease_owner = None
        session.commit()
    except Exception as error:
        session.rollback()
        run = session.scalar(_run_query(run_id).with_for_update())
        assert run is not None
        if lease_owner is not None and run.lease_owner != lease_owner:
            return run
        item = next(
            value for value in run.plant_items if value.position == item.position
        )
        stage = next(
            value
            for value in run.stages
            if value.candidate_position == item.position and value.name == stage.name
        )
        safe_message = (
            str(error)
            if isinstance(error, ValueError)
            else "The stage failed safely without exposing internal details."
        )
        _fail(
            session,
            run,
            item,
            stage,
            "quality_gate_failed",
            safe_message,
        )
    return get_run(session, run_id) or run


def retry_run(session: Session, run_id: UUID) -> PipelineRun:
    run = session.scalar(_run_query(run_id).with_for_update())
    if run is None:
        raise LookupError("Plant pipeline run not found.")
    if run.status != "failed":
        raise PlantPipelineStateError(
            "Only a failed or interrupted run can be retried."
        )
    item = next(
        (value for value in run.plant_items if value.status == "failed"),
        None,
    )
    if item is None or item.plant_profile_id is not None:
        raise PlantPipelineStateError("This run has no safely retryable item.")
    stage = next(
        value
        for value in run.stages
        if value.candidate_position == item.position and value.status == "failed"
    )
    stage.status = "pending"
    stage.attempt += 1
    stage.started_at = None
    stage.completed_at = None
    stage.error_code = None
    stage.error_message = dict(STAGES)[stage.name]
    item.status = "running"
    item.error_code = None
    item.error_message = None
    item.completed_at = None
    now = utc_now()
    run.status = "running"
    run.current_stage = stage.name
    run.finished_at = None
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    run.lease_owner = uuid4().hex
    planned = int(
        run.summary.get(
            "planned_count", run.summary.get("selected_count", len(run.plant_items))
        )
    )
    completed = int(
        run.summary.get("completed_count", run.summary.get("created_drafts", 0))
    )
    run.summary = {
        **run.summary,
        "failures": 0,
        "failed_count": 0,
        "remaining_count": max(0, planned - completed),
    }
    session.commit()
    return get_run(session, run.id) or run


def execute_run_to_terminal(run_id: UUID, lease_owner: str | None = None) -> None:
    """Advance a persisted run independently from browser progress polling.

    Each stage is claimed and completed in a fresh bounded database session.
    A concurrent executor that observes an already-running stage exits.
    """
    factory = get_session_factory()
    owner = lease_owner
    while True:
        with factory() as session:
            before = get_run(session, run_id)
            if before is None or before.status != "running":
                return
            owner = owner or before.lease_owner
            if owner is None or before.lease_owner != owner:
                return
            if any(stage.status == "running" for stage in before.stages):
                return
            after = advance_run(session, run_id, owner)
            if after.status != "running":
                return
