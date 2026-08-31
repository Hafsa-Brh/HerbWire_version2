# ruff: noqa: E501
from datetime import datetime, timezone
from time import perf_counter

from backend.app.collectors.providers.base import (
    CollectedDiscoveryRecord,
    CollectionProvider,
)
from backend.app.collectors.providers.fixture import FixtureDiscoveryProvider
from backend.app.models.encyclopedia import (
    PipelineRun,
    PipelineStageResult,
    SourceRecord,
)
from backend.app.models.source import Source
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

PIPELINE_STAGES = [
    "collect",
    "normalize",
    "deduplicate",
    "classify_relevance",
    "attach_provenance",
    "create_editorial_review_item",
    "hold_for_human_review",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _source(session: Session) -> Source:
    source = session.scalar(
        select(Source).where(Source.identifier == "fixture-discovery")
    )
    if source is None:
        source = Source(
            identifier="fixture-discovery",
            name="HerbWire deterministic fixture collector",
            base_url="https://example.org/fixtures",
            status="approved",
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(source)
        session.flush()
    return source


def _stage(
    run: PipelineRun, name: str, status: str, start: float, **extra
) -> PipelineStageResult:
    return PipelineStageResult(
        pipeline_run_id=run.id,
        name=name,
        status=status,
        attempt=1,
        duration_ms=max(0, int((perf_counter() - start) * 1000)),
        input_refs=extra.get("input_refs", []),
        output_refs=extra.get("output_refs", []),
        error_code=extra.get("error_code"),
        error_message=extra.get("error_message"),
        created_at=_now(),
    )


def _validate(record: CollectedDiscoveryRecord) -> str | None:
    if (
        not record.external_identifier
        or not record.canonical_url
        or not record.title
        or not record.text
    ):
        return "missing_required_field"
    return None


def _is_relevant(record: CollectedDiscoveryRecord) -> bool:
    haystack = f"{record.title} {record.text} {record.plant_hint or ''}".casefold()
    return any(
        term in haystack
        for term in (
            "medicinal plant",
            "traditional medicine",
            "chamomile",
            "peppermint",
            "ginger",
        )
    )


def run_fixture_pipeline(
    session: Session, mode: str = "success", provider: CollectionProvider | None = None
) -> PipelineRun:
    idempotency_key = f"fixture-discovery:{mode}:2026-08-30"
    existing = session.scalar(
        select(PipelineRun)
        .where(PipelineRun.idempotency_key == idempotency_key)
        .options(selectinload(PipelineRun.stages))
    )
    if existing is not None:
        return existing

    provider = provider or FixtureDiscoveryProvider(mode)
    run = PipelineRun(
        pipeline_type="discovery_brief",
        trigger="manual_dev_fixture",
        provider=provider.name,
        idempotency_key=idempotency_key,
        status="running",
        current_stage="collect",
        summary={},
        started_at=_now(),
    )
    session.add(run)
    session.flush()

    try:
        start = perf_counter()
        records = provider.collect()
        session.add(
            _stage(
                run,
                "collect",
                "succeeded",
                start,
                output_refs=[r.external_identifier for r in records],
            )
        )
    except Exception:
        session.add(
            _stage(
                run,
                "collect",
                "failed",
                perf_counter(),
                error_code="source_failure",
                error_message="Provider failed without exposing response details.",
            )
        )
        run.status = "failed"
        run.current_stage = "collect"
        run.finished_at = _now()
        run.summary = {"records_collected": 0, "review_items_created": 0}
        session.commit()
        return run

    valid_records = []
    malformed = 0
    for record in records:
        error = _validate(record)
        if error:
            malformed += 1
        else:
            valid_records.append(record)
    session.add(
        _stage(
            run,
            "normalize",
            "failed" if malformed and not valid_records else "succeeded",
            perf_counter(),
            output_refs=[r.external_identifier for r in valid_records],
            error_code="malformed_record" if malformed else None,
            error_message="One or more fixture records were malformed."
            if malformed
            else None,
        )
    )

    relevant = [record for record in valid_records if _is_relevant(record)]
    session.add(
        _stage(
            run,
            "classify_relevance",
            "held" if not relevant else "succeeded",
            perf_counter(),
            output_refs=[r.external_identifier for r in relevant],
        )
    )

    source = _source(session)
    new_records = []
    for record in relevant:
        existing_record = session.scalar(
            select(SourceRecord).where(
                SourceRecord.canonical_url == record.canonical_url
            )
        )
        if existing_record is None:
            existing_record = SourceRecord(
                source_id=source.id,
                external_identifier=record.external_identifier,
                url=record.url,
                canonical_url=record.canonical_url,
                title=record.title,
                publisher=record.publisher,
                source_type=record.source_type,
                original_language=record.original_language,
                license_status=record.license_status,
                supports={"discovery": True, "fixture": True},
                permitted_extract=record.text,
                parser_version="fixture-provider-v1",
                content_hash=record.external_identifier,
                source_publication_date=None,
                collected_at=_now(),
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(existing_record)
            session.flush()
        new_records.append(existing_record)
    session.add(
        _stage(
            run,
            "deduplicate",
            "succeeded",
            perf_counter(),
            output_refs=[str(r.id) for r in new_records],
        )
    )
    session.add(
        _stage(
            run,
            "attach_provenance",
            "succeeded" if new_records else "skipped",
            perf_counter(),
            output_refs=[str(r.id) for r in new_records],
        )
    )

    held_record_ids = [str(source_record.id) for source_record in new_records]
    session.add(
        _stage(
            run,
            "create_editorial_review_item",
            "skipped",
            perf_counter(),
            output_refs=[],
            error_code="plant_profile_required",
            error_message=(
                "Editorial review rows are reserved for plant profiles in Milestone 2. "
                "Discovery fixture records stay held in pipeline state until article review "
                "storage is designed."
            ),
        )
    )
    session.add(
        _stage(
            run,
            "hold_for_human_review",
            "held",
            perf_counter(),
            output_refs=held_record_ids,
        )
    )

    run.status = "held" if held_record_ids else "partial"
    run.current_stage = "hold_for_human_review"
    run.finished_at = _now()
    run.summary = {
        "records_collected": len(records),
        "records_valid": len(valid_records),
        "records_relevant": len(relevant),
        "held_source_records": len(held_record_ids),
        "review_items_created": 0,
        "auto_published": 0,
    }
    session.commit()
    session.refresh(run)
    return run
