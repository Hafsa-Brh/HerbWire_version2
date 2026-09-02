from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from time import perf_counter

from backend.app.collectors.providers.base import CollectionProvider, CollectionRequest
from backend.app.collectors.providers.pubmed import PubMedCollectionError
from backend.app.domains.discovery.contracts import EvidencePackage
from backend.app.domains.discovery.deduplication import (
    get_or_create_source_record,
    require_pubmed_source,
)
from backend.app.domains.discovery.drafting import DeterministicDiscoveryDraftWriter
from backend.app.domains.discovery.enrichment import DeterministicEvidenceEnricher
from backend.app.domains.discovery.normalization import (
    NormalizationError,
    normalize_record,
)
from backend.app.domains.discovery.qa import evaluate_draft
from backend.app.domains.discovery.relevance import PlantTerm, detect_relevance
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryArticleSource,
    DiscoveryEvent,
    EditorialReview,
    PipelineRun,
    PipelineStageResult,
    PlantProfile,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

DISCOVERY_STAGES = (
    "collect",
    "normalize",
    "deduplicate",
    "detect_relevance",
    "enrich_evidence",
    "draft_article",
    "qa_policy_gate",
    "queue_editorial_review",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def discovery_idempotency_key(request: CollectionRequest) -> str:
    value = (
        f"pubmed:medicinal-plants-v1:{request.start_date.isoformat()}:"
        f"{request.end_date.isoformat()}:{request.max_records}:{request.date_type}"
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_run(session: Session, run_id: uuid.UUID) -> PipelineRun:
    return session.scalars(
        select(PipelineRun)
        .where(PipelineRun.id == run_id)
        .options(selectinload(PipelineRun.stages))
    ).one()


def _stage(
    session: Session,
    run: PipelineRun,
    name: str,
    status: str,
    started: float,
    input_count: int,
    output_count: int,
    input_refs: list | None = None,
    output_refs: list | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    result = session.scalar(
        select(PipelineStageResult).where(
            PipelineStageResult.pipeline_run_id == run.id,
            PipelineStageResult.name == name,
        )
    )
    if result is None:
        result = PipelineStageResult(
            pipeline_run_id=run.id,
            name=name,
            status=status,
            attempt=1,
            duration_ms=0,
            input_count=input_count,
            output_count=output_count,
            input_refs=input_refs or [],
            output_refs=output_refs or [],
            created_at=utc_now(),
        )
        session.add(result)
    else:
        result.attempt += 1
        result.status = status
        result.input_count = input_count
        result.output_count = output_count
        result.input_refs = input_refs or []
        result.output_refs = output_refs or []
    result.duration_ms = max(0, int((perf_counter() - started) * 1000))
    result.error_code = error_code
    result.error_message = error_message
    run.current_stage = name
    session.commit()


def _plant_terms(session: Session) -> list[PlantTerm]:
    return [
        PlantTerm(
            common_name=profile.display_common_name,
            scientific_name=profile.accepted_scientific_name,
        )
        for profile in session.scalars(select(PlantProfile)).all()
    ]


def _existing_or_new_run(
    session: Session, request: CollectionRequest, trigger: str
) -> tuple[PipelineRun, bool]:
    key = discovery_idempotency_key(request)
    existing = session.scalar(
        select(PipelineRun).where(PipelineRun.idempotency_key == key)
    )
    if existing is not None:
        if existing.status == "failed":
            existing.status = "running"
            existing.finished_at = None
            existing.summary = {
                **existing.summary,
                "retry_count": existing.summary.get("retry_count", 0) + 1,
            }
            session.commit()
            return existing, True
        return _load_run(session, existing.id), False

    run = PipelineRun(
        pipeline_type="pubmed_discovery_review",
        trigger=trigger,
        provider="pubmed",
        idempotency_key=key,
        status="running",
        current_stage="collect",
        summary={
            "request": {
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
                "max_records": request.max_records,
                "date_type": request.date_type,
            },
            "auto_published": 0,
        },
        started_at=utc_now(),
    )
    session.add(run)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return session.scalars(
            select(PipelineRun)
            .where(PipelineRun.idempotency_key == key)
            .options(selectinload(PipelineRun.stages))
        ).one(), False
    return run, True


def _event_for_record(
    session: Session, source_record_id: uuid.UUID, decision
) -> DiscoveryEvent:
    event = session.scalar(
        select(DiscoveryEvent).where(
            DiscoveryEvent.source_record_id == source_record_id
        )
    )
    if event is None:
        event = DiscoveryEvent(
            source_record_id=source_record_id,
            status="relevant" if decision.relevant else "irrelevant",
            category=decision.category,
            relevance_confidence=decision.confidence,
            reasons=list(decision.reasons),
            evidence_signals=list(decision.evidence_signals),
            detected_entities=list(decision.entities),
            evidence_package={},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(event)
        session.flush()
    return event


def _article_for_evidence(
    session: Session,
    event: DiscoveryEvent,
    source_record_id: uuid.UUID,
    normalized,
    evidence: EvidencePackage,
) -> DiscoveryArticle:
    article = session.scalar(
        select(DiscoveryArticle).where(DiscoveryArticle.event_id == event.id)
    )
    if article is not None:
        return article
    draft = DeterministicDiscoveryDraftWriter().write(normalized, evidence)
    checksum = hashlib.sha256(
        json.dumps(
            draft.checksum_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    article = DiscoveryArticle(
        event_id=event.id,
        slug=draft.slug,
        status="draft",
        headline=draft.headline,
        standfirst=draft.standfirst,
        body_blocks=list(draft.body_blocks),
        limitations=list(draft.limitations),
        safety_context=draft.safety_context,
        cannot_conclude=list(draft.cannot_conclude),
        qa_payload={},
        content_checksum=checksum,
        version=1,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(article)
    session.flush()
    session.add(
        DiscoveryArticleSource(
            discovery_article_id=article.id,
            source_record_id=source_record_id,
            support_role="primary_evidence",
            evidence_locations=list(evidence.excerpts),
        )
    )
    return article


def _queue_review(
    session: Session, article: DiscoveryArticle, qa, evidence: EvidencePackage
) -> EditorialReview:
    review = session.scalar(
        select(EditorialReview).where(
            EditorialReview.discovery_article_id == article.id
        )
    )
    if review is not None:
        return review
    status = "needs_review" if qa.passed else "held"
    article.status = status
    article.qa_payload = {
        "provider": "deterministic-policy-v1",
        "passed": qa.passed,
        "reason_codes": list(qa.reason_codes),
        "checklist": qa.checklist,
    }
    review = EditorialReview(
        plant_profile_id=None,
        discovery_article_id=article.id,
        content_type="discovery_article",
        status=status,
        decision_reason=(None if qa.passed else ", ".join(qa.reason_codes)),
        review_payload={
            "category": evidence.category,
            "evidence_type": evidence.evidence_type,
            "source_record_ids": [evidence.source_record_id],
            "qa_reason_codes": list(qa.reason_codes),
        },
        created_at=utc_now(),
    )
    session.add(review)
    session.flush()
    return review


def _fail_run(
    session: Session, run_id: uuid.UUID, stage_name: str, error: Exception
) -> PipelineRun:
    session.rollback()
    run = session.get_one(PipelineRun, run_id)
    code = getattr(error, "code", "unexpected_pipeline_error")
    message = (
        str(error)
        if isinstance(error, (PubMedCollectionError, NormalizationError))
        else "The stage failed without exposing internal details."
    )
    _stage(
        session,
        run,
        stage_name,
        "failed",
        perf_counter(),
        input_count=0,
        output_count=0,
        error_code=code,
        error_message=message[:500],
    )
    run.status = "failed"
    run.finished_at = utc_now()
    run.summary = {**run.summary, "failed_stage": stage_name, "error_code": code}
    session.commit()
    return _load_run(session, run.id)


def run_discovery_pipeline(
    session: Session,
    request: CollectionRequest,
    provider: CollectionProvider,
    trigger: str = "manual_admin",
) -> PipelineRun:
    run, should_execute = _existing_or_new_run(session, request, trigger)
    if not should_execute:
        return run

    current_stage = "collect"
    try:
        started = perf_counter()
        collected = provider.collect(request)
        _stage(
            session,
            run,
            "collect",
            "succeeded",
            started,
            input_count=0,
            output_count=len(collected),
            output_refs=[record.external_identifier for record in collected],
        )

        current_stage = "normalize"
        started = perf_counter()
        normalized = [normalize_record(record) for record in collected]
        _stage(
            session,
            run,
            "normalize",
            "succeeded",
            started,
            input_count=len(collected),
            output_count=len(normalized),
            output_refs=[record.external_identifier for record in normalized],
        )

        current_stage = "deduplicate"
        started = perf_counter()
        source = require_pubmed_source(session)
        persisted = []
        created_records = 0
        for record in normalized:
            source_record, created = get_or_create_source_record(
                session, source, record, utc_now()
            )
            persisted.append((record, source_record))
            created_records += int(created)
        _stage(
            session,
            run,
            "deduplicate",
            "succeeded",
            started,
            input_count=len(normalized),
            output_count=created_records,
            output_refs=[str(item.id) for _, item in persisted],
        )

        current_stage = "detect_relevance"
        started = perf_counter()
        terms = _plant_terms(session)
        decisions = []
        relevant = []
        for record, source_record in persisted:
            decision = detect_relevance(record, terms)
            event = _event_for_record(session, source_record.id, decision)
            decisions.append((record, source_record, event, decision))
            if decision.relevant:
                relevant.append((record, source_record, event, decision))
        _stage(
            session,
            run,
            "detect_relevance",
            "succeeded",
            started,
            input_count=len(persisted),
            output_count=len(relevant),
            output_refs=[str(event.id) for _, _, event, _ in decisions],
        )

        current_stage = "enrich_evidence"
        started = perf_counter()
        enricher = DeterministicEvidenceEnricher()
        enriched = []
        for record, source_record, event, decision in relevant:
            evidence = enricher.enrich(record, str(source_record.id), decision)
            event.status = "enriched"
            event.evidence_package = evidence.as_dict()
            event.updated_at = utc_now()
            enriched.append((record, source_record, event, evidence))
        _stage(
            session,
            run,
            "enrich_evidence",
            "succeeded" if enriched else "skipped",
            started,
            input_count=len(relevant),
            output_count=len(enriched),
            output_refs=[str(event.id) for _, _, event, _ in enriched],
        )

        current_stage = "draft_article"
        started = perf_counter()
        drafted = []
        for record, source_record, event, evidence in enriched:
            article = _article_for_evidence(
                session, event, source_record.id, record, evidence
            )
            drafted.append((article, evidence))
        _stage(
            session,
            run,
            "draft_article",
            "succeeded" if drafted else "skipped",
            started,
            input_count=len(enriched),
            output_count=len(drafted),
            output_refs=[str(article.id) for article, _ in drafted],
        )

        current_stage = "qa_policy_gate"
        started = perf_counter()
        evaluated = []
        passed = 0
        for article, evidence in drafted:
            draft = DeterministicDiscoveryDraftWriter().write(
                next(
                    record
                    for record, _, event, _ in enriched
                    if event.id == article.event_id
                ),
                evidence,
            )
            qa = evaluate_draft(draft, evidence)
            evaluated.append((article, evidence, qa))
            passed += int(qa.passed)
        _stage(
            session,
            run,
            "qa_policy_gate",
            "succeeded"
            if passed == len(evaluated)
            else ("held" if evaluated else "skipped"),
            started,
            input_count=len(drafted),
            output_count=passed,
            output_refs=[str(article.id) for article, _, qa in evaluated if qa.passed],
            error_code="qa_hold" if evaluated and passed != len(evaluated) else None,
            error_message="One or more drafts failed closed at the policy gate."
            if evaluated and passed != len(evaluated)
            else None,
        )

        current_stage = "queue_editorial_review"
        started = perf_counter()
        reviews = [
            _queue_review(session, article, qa, evidence)
            for article, evidence, qa in evaluated
        ]
        _stage(
            session,
            run,
            "queue_editorial_review",
            "succeeded" if passed else ("held" if reviews else "skipped"),
            started,
            input_count=len(evaluated),
            output_count=passed,
            output_refs=[str(review.id) for review in reviews],
        )

        run.status = "succeeded" if passed == len(evaluated) else "held"
        run.finished_at = utc_now()
        run.summary = {
            **run.summary,
            "records_collected": len(collected),
            "records_normalized": len(normalized),
            "records_created": created_records,
            "records_duplicate": len(normalized) - created_records,
            "records_relevant": len(relevant),
            "records_irrelevant": len(persisted) - len(relevant),
            "drafts_created_or_reused": len(drafted),
            "review_ready": passed,
            "held": len(evaluated) - passed,
            "auto_published": 0,
        }
        session.commit()
        return _load_run(session, run.id)
    except Exception as error:
        return _fail_run(session, run.id, current_stage, error)


def list_discovery_articles(session: Session) -> list[DiscoveryArticle]:
    return list(
        session.scalars(
            select(DiscoveryArticle)
            .options(
                selectinload(DiscoveryArticle.event).selectinload(
                    DiscoveryEvent.source_record
                ),
                selectinload(DiscoveryArticle.sources).selectinload(
                    DiscoveryArticleSource.source_record
                ),
                selectinload(DiscoveryArticle.reviews),
            )
            .order_by(DiscoveryArticle.created_at.desc())
        ).all()
    )


def get_discovery_article(
    session: Session, article_id: uuid.UUID
) -> DiscoveryArticle | None:
    return session.scalar(
        select(DiscoveryArticle)
        .where(DiscoveryArticle.id == article_id)
        .options(
            selectinload(DiscoveryArticle.event).selectinload(
                DiscoveryEvent.source_record
            ),
            selectinload(DiscoveryArticle.sources).selectinload(
                DiscoveryArticleSource.source_record
            ),
            selectinload(DiscoveryArticle.reviews),
        )
    )


def decide_discovery_article(
    session: Session,
    article_id: uuid.UUID,
    decision: str,
    reviewer_name: str,
    reason: str | None,
) -> DiscoveryArticle:
    article = get_discovery_article(session, article_id)
    if article is None:
        raise LookupError("Discovery article not found.")
    if article.status == "published":
        raise ValueError(
            "Published discovery content cannot be changed by this action."
        )
    if decision not in {"approved", "held", "rejected"}:
        raise ValueError("Unsupported editorial decision.")
    if decision == "approved" and not article.qa_payload.get("passed", False):
        raise ValueError("A QA-held discovery cannot be approved.")
    if decision in {"held", "rejected"} and not (reason or "").strip():
        raise ValueError("A reason is required for held or rejected decisions.")
    review = article.reviews[0]
    article.status = decision
    article.reviewed_at = utc_now()
    review.status = decision
    review.reviewer_name = reviewer_name.strip() or "Editor"
    review.decision_reason = (reason or "").strip() or None
    review.decided_at = utc_now()
    session.commit()
    return get_discovery_article(session, article_id)  # type: ignore[return-value]
