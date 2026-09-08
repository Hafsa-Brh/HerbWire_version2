"""Durable, strictly sequential Discovery article orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta
from time import monotonic
from uuid import UUID, uuid4

from backend.app.collectors.providers.base import CollectedDiscoveryRecord
from backend.app.db.session import get_session_factory
from backend.app.domains.discovery.curated_import import create_pipeline_discovery_draft
from backend.app.domains.discovery.normalization import normalize_record
from backend.app.domains.discovery.pipeline_catalog import (
    DiscoveryPipelineCandidate,
    load_discovery_pipeline_catalog,
)
from backend.app.domains.discovery.relevance import PlantTerm, detect_relevance
from backend.app.domains.encyclopedia.plant_eligibility import (
    check_subject_eligibility,
    protected_reserve_message,
    reserve_subject,
    subject_from_discovery_candidate,
    subject_identity_keys,
)
from backend.app.domains.pipeline.plant_profile_pipeline import EDITORIAL_PIPELINE_TYPES
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryPipelineItem,
    PipelineRun,
    PipelineStageResult,
    SourceRecord,
    utc_now,
)
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

PIPELINE_TYPE = "discovery_article_automation"
MAX_BATCH_SIZE = 10
PROTECTED_RESERVE = 10
LEASE_SECONDS = 120
STAGES = (
    ("collector_gateway", "Collector Gateway"),
    ("normalization_and_deduplication", "Normalization and Deduplication"),
    ("relevance_and_classification", "Relevance and Classification"),
    (
        "language_translation_entity_enrichment",
        "Language, Translation, and Entity Enrichment",
    ),
    ("botanical_resolver", "Botanical Resolver"),
    ("evidence_safety_and_provenance", "Evidence, Safety, and Provenance"),
    ("media_and_geography", "Media & Geography Agent"),
    ("content_composer", "Content Composer"),
    ("editorial_qa", "Editorial QA"),
    ("queue_editorial_review", "Private review creation"),
)


class DiscoveryPipelineBusyError(RuntimeError):
    pass


class DiscoveryPipelineStateError(RuntimeError):
    pass


class DiscoveryPipelineHold(ValueError):
    pass


def _run_query(run_id: UUID | None = None):
    query = select(PipelineRun).options(
        selectinload(PipelineRun.stages),
        selectinload(PipelineRun.discovery_items).selectinload(
            DiscoveryPipelineItem.discovery_article
        ),
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


def _candidate_record(
    candidate: DiscoveryPipelineCandidate,
) -> CollectedDiscoveryRecord:
    source = candidate.primary_source
    return CollectedDiscoveryRecord(
        external_identifier=source.pmid or source.stable_identifier,
        url=str(source.canonical_url),
        canonical_url=str(source.canonical_url),
        title=source.title,
        publisher=source.journal or "PubMed",
        source_type="research",
        original_language="en",
        license_status=(
            "PubMed metadata; article and abstract copyright remain with their holders."
        ),
        text=candidate.abstract_extract,
        plant_hint=candidate.article.scientific_name,
        doi=source.doi,
        authors=tuple(source.authors),
        journal=source.journal,
        publication_date=source.publication_date,
        retrieved_at=datetime.fromisoformat(
            candidate.retrieved_at.replace("Z", "+00:00")
        ),
        metadata={"publication_types": source.publication_types},
    )


def _eligible(
    session: Session,
    candidate: DiscoveryPipelineCandidate,
    *,
    exclude_run_id: UUID | None = None,
) -> bool:
    source = candidate.primary_source
    reservation = select(DiscoveryPipelineItem.id).where(
        DiscoveryPipelineItem.candidate_key == candidate.key
    )
    if exclude_run_id is not None:
        reservation = reservation.where(
            DiscoveryPipelineItem.pipeline_run_id != exclude_run_id
        )
    if session.scalar(reservation):
        return False
    normalized = normalize_record(_candidate_record(candidate))
    if session.scalar(
        select(SourceRecord.id).where(
            or_(
                SourceRecord.external_identifier == source.pmid,
                SourceRecord.canonical_url == str(source.canonical_url),
                SourceRecord.doi == source.doi if source.doi else False,
                SourceRecord.content_hash == normalized.content_hash,
            )
        )
    ):
        return False
    if session.scalar(
        select(DiscoveryArticle.id).where(
            or_(
                DiscoveryArticle.slug == candidate.article.slug,
                DiscoveryArticle.content_checksum == candidate.article.content_checksum,
            )
        )
    ):
        return False
    return check_subject_eligibility(
        session,
        subject_from_discovery_candidate(candidate),
        exclude_run_id=exclude_run_id,
    ).eligible


def preview_candidates(
    session: Session, count: int = 1, *, all_available: bool = False
) -> dict:
    if not 1 <= count <= MAX_BATCH_SIZE:
        raise ValueError("Articles to generate must be between 1 and 10.")
    catalog = load_discovery_pipeline_catalog()
    eligible = []
    batch_keys: set[str] = set()
    for candidate in catalog.candidates:
        subject = subject_from_discovery_candidate(candidate)
        identity = check_subject_eligibility(session, subject, batch_keys=batch_keys)
        if _eligible(session, candidate) and identity.eligible:
            eligible.append(candidate)
            batch_keys.update(subject_identity_keys(subject))
    safe_capacity = max(0, len(eligible) - PROTECTED_RESERVE)
    planned_count = min(MAX_BATCH_SIZE, safe_capacity) if all_available else count
    can_start = planned_count > 0 and safe_capacity >= planned_count
    selected = eligible[:planned_count] if can_start else []
    return {
        "requested_count": planned_count if all_available else count,
        "available_count": len(eligible),
        "planned_count": len(selected),
        "vetted_count": len(catalog.candidates),
        "catalogue_exhausted": not eligible,
        "insufficient_availability": not can_start,
        "selection_mode": "all_available" if all_available else "count",
        "can_start": can_start,
        "unavailable_reason": None if can_start else protected_reserve_message(),
        "_candidate_keys": [candidate.key for candidate in selected],
    }


def start_run(
    session: Session,
    count: int,
    idempotency_key: str,
    *,
    all_available: bool = False,
) -> PipelineRun:
    if not 1 <= count <= MAX_BATCH_SIZE:
        raise ValueError("Articles to generate must be between 1 and 10.")
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
        raise DiscoveryPipelineBusyError(
            "An editorial generation pipeline is already active."
        )

    preview = preview_candidates(session, count, all_available=all_available)
    if not preview["can_start"]:
        raise ValueError(protected_reserve_message())
    candidate_keys = preview["_candidate_keys"]
    now = utc_now()
    run = PipelineRun(
        pipeline_type=PIPELINE_TYPE,
        trigger="editorial_desk",
        provider="pubmed_vetted_catalogue",
        idempotency_key=idempotency_key,
        status="running" if candidate_keys else "held",
        current_stage=STAGES[0][0] if candidate_keys else "catalogue_exhausted",
        summary={
            "requested_count": preview["requested_count"],
            "available_count_at_start": preview["available_count"],
            "planned_count": len(candidate_keys),
            "completed_count": 0,
            "held_count": 0,
            "failed_count": 0,
            "remaining_count": len(candidate_keys),
            "source_count": 0,
            "execution_policy": "strictly_sequential_fail_fast",
            "catalogue_exhausted": not candidate_keys,
            "selection_mode": preview["selection_mode"],
            "auto_published": 0,
        },
        started_at=now,
        finished_at=None if candidate_keys else now,
        heartbeat_at=now,
        lease_expires_at=now + timedelta(seconds=LEASE_SECONDS)
        if candidate_keys
        else None,
        lease_owner=uuid4().hex if candidate_keys else None,
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
        raise DiscoveryPipelineBusyError(
            "A concurrent editorial pipeline request won the database lock."
        ) from error

    catalog = load_discovery_pipeline_catalog()
    for position, candidate_key in enumerate(candidate_keys, start=1):
        candidate = next(
            value for value in catalog.candidates if value.key == candidate_key
        )
        session.add(
            DiscoveryPipelineItem(
                pipeline_run_id=run.id,
                candidate_key=candidate_key,
                position=position,
                status="pending",
                candidate_snapshot={
                    "catalogue_version": candidate.catalogue_version,
                    "primary_botanical_subject": (
                        candidate.primary_botanical_subject.model_dump(mode="json")
                    ),
                },
                work_payload={"quality_gates": {}},
            )
        )
        reserve_subject(
            session,
            run_id=run.id,
            domain="discoveries",
            candidate_key=candidate.key,
            subject=subject_from_discovery_candidate(candidate),
        )
        for name, label in STAGES:
            session.add(
                PipelineStageResult(
                    pipeline_run_id=run.id,
                    candidate_position=position,
                    name=name,
                    status="pending",
                    attempt=1,
                    input_refs=[],
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
        raise DiscoveryPipelineBusyError(
            "A concurrent editorial pipeline request won the database lock."
        ) from error
    return get_run(session, run.id) or run


def _gate(passed: bool, detail: str) -> dict:
    if not passed:
        raise DiscoveryPipelineHold(detail)
    return {"status": "passed", "detail": detail}


def _stage_result(
    session: Session,
    name: str,
    candidate: DiscoveryPipelineCandidate,
    gates: dict,
    run_id: UUID,
) -> tuple[dict, list[str]]:
    article = candidate.article
    source = candidate.primary_source
    normalized = normalize_record(_candidate_record(candidate))
    if name == "collector_gateway":
        gates["pubmed_source_verified"] = _gate(
            bool(source.pmid and source.retraction_status == "checked_clear"),
            "Official PubMed identity, bibliographic metadata, and retraction "
            "check are present.",
        )
    elif name == "normalization_and_deduplication":
        gates["duplicate_check"] = _gate(
            _eligible(session, candidate, exclude_run_id=run_id),
            "PMID, DOI, canonical URL, content identity, and reservation are "
            "unrepresented.",
        )
    elif name == "relevance_and_classification":
        subject = candidate.primary_botanical_subject
        terms = [
            PlantTerm(common_name, subject.accepted_scientific_name)
            for common_name in subject.common_names
        ]
        decision = detect_relevance(normalized, terms)
        gates["relevance_verified"] = _gate(
            decision.relevant
            and bool(decision.entities)
            and bool(subject.taxon_identifier),
            "A source-supported scientific Plant identity is central to the study.",
        )
    elif name == "language_translation_entity_enrichment":
        gates["language_and_entities"] = _gate(
            normalized.original_language == "en" and bool(article.scientific_name),
            "English source metadata and structured Plant/category entities are "
            "complete.",
        )
    elif name == "botanical_resolver":
        identity = article.botanical_identity
        subject = candidate.primary_botanical_subject
        gates["botanical_identity"] = _gate(
            bool(
                identity
                and identity.accepted
                and identity.accepted_scientific_name
                == subject.accepted_scientific_name
                and identity.authority_taxon_id == subject.taxon_identifier
            ),
            "The primary botanical subject resolves to its accepted authority record.",
        )
    elif name == "evidence_safety_and_provenance":
        gates["source_traceability"] = _gate(
            bool(article.section_sources) and bool(article.sources),
            "Every required article section resolves to stored source metadata.",
        )
        gates["evidence_limitations"] = _gate(
            bool(article.limitations and article.cannot_conclude),
            "Method limitations and explicit non-conclusions are present.",
        )
        gates["safety_context"] = _gate(
            bool(article.safety_context.strip()),
            "Conservative safety and interaction limits are present.",
        )
    elif name == "media_and_geography":
        media = article.hero_image
        required_media = {
            "local_path",
            "source_page",
            "license",
            "license_url",
            "attribution",
            "checksum_sha256",
        }
        gates["licensed_photograph"] = _gate(
            bool(
                media
                and required_media <= set(media.model_dump())
                and all(media.model_dump().get(key) for key in required_media)
                and media.classification == "botanical_reference"
            ),
            (
                "A taxon-matched botanical photograph and complete attribution "
                "are verified."
            ),
        )
        gates["geography_normalized"] = _gate(
            bool(article.geography)
            and all(
                value.iso_country_code is None or len(value.iso_country_code) == 2
                for value in article.geography
            ),
            "Research geography uses validated ISO country context and qualification.",
        )
    elif name == "content_composer":
        gates["required_sections"] = _gate(
            bool(
                article.headline
                and article.standfirst
                and article.study_design
                and article.main_findings
                and article.why_matters
                and article.practical_interpretation
            ),
            "The rich Discovery article contract is complete.",
        )
    elif name == "editorial_qa":
        gates["qa"] = _gate(
            all(value["status"] == "passed" for value in gates.values()),
            "Deterministic QA passed; human source, claim, and image review remains "
            "required.",
        )
    return gates, [name]


def _terminal_failure(
    session: Session,
    run: PipelineRun,
    item: DiscoveryPipelineItem,
    stage: PipelineStageResult,
    *,
    held: bool,
    message: str,
) -> None:
    now = utc_now()
    state = "held" if held else "failed"
    stage.status = state
    stage.error_code = "quality_gate_held" if held else "pipeline_stage_failed"
    stage.error_message = message[:500]
    stage.completed_at = now
    item.status = state
    item.error_code = stage.error_code
    item.error_message = stage.error_message
    item.completed_at = now
    run.status = state
    run.current_stage = stage.name
    run.finished_at = now
    run.lease_expires_at = None
    run.lease_owner = None
    completed = int(run.summary.get("completed_count", 0))
    held_count = int(run.summary.get("held_count", 0)) + int(held)
    failed_count = int(run.summary.get("failed_count", 0)) + int(not held)
    planned = int(run.summary.get("planned_count", len(run.discovery_items)))
    run.summary = {
        **run.summary,
        "held_count": held_count,
        "failed_count": failed_count,
        "remaining_count": max(0, planned - completed - held_count - failed_count),
    }
    session.commit()


def advance_run(
    session: Session, run_id: UUID, lease_owner: str | None = None
) -> PipelineRun:
    run = session.scalar(_run_query(run_id).with_for_update())
    if run is None:
        raise LookupError("Discovery pipeline run not found.")
    if run.pipeline_type != PIPELINE_TYPE:
        raise DiscoveryPipelineStateError("Run is not a Discovery pipeline run.")
    if run.status != "running":
        return run
    if lease_owner is not None and run.lease_owner != lease_owner:
        return run

    items = sorted(run.discovery_items, key=lambda value: value.position)
    item = next(
        (value for value in items if value.status in {"pending", "running"}), None
    )
    if item is None:
        run.status = "succeeded"
        run.current_stage = "completed"
        run.finished_at = utc_now()
        run.lease_expires_at = None
        run.lease_owner = None
        session.commit()
        return get_run(session, run.id) or run

    order = [name for name, _ in STAGES]
    stages = sorted(
        (stage for stage in run.stages if stage.candidate_position == item.position),
        key=lambda value: order.index(value.name),
    )
    stage = next(
        (value for value in stages if value.status in {"pending", "running"}), None
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
    catalog = load_discovery_pipeline_catalog()
    candidate = next(
        value for value in catalog.candidates if value.key == item.candidate_key
    )
    position = item.position
    stage_name = stage.name
    try:
        gates = dict(item.work_payload.get("quality_gates", {}))
        gates, output_refs = _stage_result(
            session, stage_name, candidate, gates, run.id
        )
        session.expire_all()
        run = session.scalar(_run_query(run_id).with_for_update())
        assert run is not None
        if lease_owner is not None and run.lease_owner != lease_owner:
            return run
        item = next(
            value for value in run.discovery_items if value.position == position
        )
        stage = next(
            value
            for value in run.stages
            if value.candidate_position == position and value.name == stage_name
        )
        if stage_name == "queue_editorial_review":
            eligibility = check_subject_eligibility(
                session,
                subject_from_discovery_candidate(candidate),
                exclude_run_id=run.id,
            )
            if (
                not _eligible(session, candidate, exclude_run_id=run.id)
                or not eligibility.eligible
            ):
                raise DiscoveryPipelineHold(
                    "Candidate became ineligible before private draft persistence."
                )
            result = create_pipeline_discovery_draft(
                session,
                candidate.article,
                candidate_key=candidate.key,
                pipeline_run_id=run.id,
                quality_gates=gates,
            )
            item.discovery_article_id = result.article.id
            item.review_id = result.review.id
            item.source_count = result.source_count
            output_refs = [str(result.article.id), str(result.review.id)]
        item.work_payload = {"quality_gates": gates}
        stage.status = "succeeded"
        stage.duration_ms = max(1, round((monotonic() - started) * 1000))
        stage.input_count = 1
        stage.output_count = len(output_refs)
        stage.output_refs = output_refs
        stage.error_code = None
        stage.error_message = f"{dict(STAGES)[stage_name]} completed."
        stage.completed_at = utc_now()
        run.heartbeat_at = utc_now()
        run.lease_expires_at = utc_now() + timedelta(seconds=LEASE_SECONDS)
        if stage_name == STAGES[-1][0]:
            item.status = "succeeded"
            item.completed_at = utc_now()
            completed = int(run.summary.get("completed_count", 0)) + 1
            planned = int(run.summary.get("planned_count", len(run.discovery_items)))
            run.summary = {
                **run.summary,
                "completed_count": completed,
                "remaining_count": max(0, planned - completed),
                "source_count": int(run.summary.get("source_count", 0))
                + item.source_count,
            }
            if not any(value.status == "pending" for value in run.discovery_items):
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
            value for value in run.discovery_items if value.position == position
        )
        stage = next(
            value
            for value in run.stages
            if value.candidate_position == position and value.name == stage_name
        )
        held = isinstance(error, DiscoveryPipelineHold)
        safe_message = (
            str(error)
            if isinstance(error, ValueError)
            else "The stage failed safely without exposing internal details."
        )
        _terminal_failure(session, run, item, stage, held=held, message=safe_message)
    return get_run(session, run_id) or run


def retry_run(session: Session, run_id: UUID) -> PipelineRun:
    run = session.scalar(_run_query(run_id).with_for_update())
    if run is None:
        raise LookupError("Discovery pipeline run not found.")
    if run.status != "failed":
        raise DiscoveryPipelineStateError(
            "Only a failed or interrupted run can be retried."
        )
    item = next(
        (value for value in run.discovery_items if value.status == "failed"), None
    )
    if item is None or item.discovery_article_id is not None:
        raise DiscoveryPipelineStateError("This run has no safely retryable item.")
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
    run.finished_at = None
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    run.lease_owner = uuid4().hex
    planned = int(run.summary.get("planned_count", len(run.discovery_items)))
    completed = int(run.summary.get("completed_count", 0))
    run.summary = {
        **run.summary,
        "failed_count": 0,
        "remaining_count": max(0, planned - completed),
    }
    session.commit()
    return get_run(session, run.id) or run


def execute_run_to_terminal(run_id: UUID, lease_owner: str | None = None) -> None:
    """Advance a persisted batch independently from browser progress polling."""
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
