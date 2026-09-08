import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.encyclopedia.plant_eligibility import (
    check_candidate_eligibility,
)
from backend.app.domains.encyclopedia.plant_pipeline_catalog import (
    load_plant_pipeline_catalog,
)
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.domains.pipeline.plant_profile_pipeline import (
    PIPELINE_TYPE,
    PlantPipelineBusyError,
    get_current_run,
    start_run,
)
from backend.app.domains.pipeline.recovery import (
    claim_recoverable_run,
    execute_claim,
)
from backend.app.models.encyclopedia import (
    DiscoveryEvent,
    EditorialReview,
    PipelineRun,
    PlantProfile,
    SourceRecord,
    utc_now,
)
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

LOGIN = {"email": "test-admin@example.invalid", "password": "test-password"}


@pytest.fixture(autouse=True)
def clean_pipeline_invariant_tables():
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "TRUNCATE plant_pipeline_items, pipeline_stage_results, pipeline_runs, "
                "editorial_reviews, plant_profile_revisions, plant_profile_sources, "
                "discovery_article_plants, discovery_article_sources, "
                "discovery_articles, discovery_events, source_records, plant_profiles "
                "CASCADE"
            )
        )
        connection.execute(
            text("DELETE FROM sources WHERE identifier IN ('powo','ema','commons')")
        )
    yield


def test_default_count_is_one_and_database_enforces_one_active_run(client) -> None:
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200
    started = client.post(
        "/api/v1/admin/plant-pipeline/runs",
        json={"idempotency_key": str(uuid.uuid4())},
    )
    assert started.status_code == 201
    assert started.json()["items"] == []
    completed = client.get(
        f"/api/v1/admin/plant-pipeline/runs/{started.json()['id']}"
    ).json()
    assert len(completed["items"]) == 1
    with get_session_factory()() as session:
        session.add(
            PipelineRun(
                pipeline_type=PIPELINE_TYPE,
                trigger="concurrency_test",
                provider="local",
                idempotency_key=str(uuid.uuid4()),
                status="running",
                current_stage="test",
                summary={},
            )
        )
        session.add(
            PipelineRun(
                pipeline_type=PIPELINE_TYPE,
                trigger="concurrency_test_second",
                provider="local",
                idempotency_key=str(uuid.uuid4()),
                status="running",
                current_stage="test",
                summary={},
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_concurrent_launches_allow_exactly_one_active_run() -> None:
    def launch(key: str) -> str:
        with get_session_factory()() as session:
            try:
                start_run(session, 1, key)
            except PlantPipelineBusyError:
                return "busy"
            return "started"

    keys = [str(uuid.uuid4()), str(uuid.uuid4())]
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(launch, keys))

    assert sorted(outcomes) == ["busy", "started"]
    with get_session_factory()() as session:
        active = session.scalars(
            select(PipelineRun).where(PipelineRun.status == "running")
        ).all()
        assert len(active) == 1


def test_stale_run_is_automatically_reclaimed_at_same_stage_boundary() -> None:
    with get_session_factory()() as session:
        run = start_run(session, 1, str(uuid.uuid4()))
        item = run.plant_items[0]
        stage = item.run.stages[0]
        item.status = "running"
        stage.status = "running"
        stage.started_at = utc_now() - timedelta(minutes=3)
        run.lease_expires_at = utc_now() - timedelta(seconds=1)
        original_run_id = run.id
        session.commit()

    with get_session_factory()() as session:
        claim = claim_recoverable_run(session)
        assert claim is not None
        assert claim.run_id == original_run_id
        recovered = get_current_run(session)
        assert recovered is not None
        recovered_stage = next(
            value for value in recovered.stages if value.name == stage.name
        )
        assert recovered.status == "running"
        assert recovered_stage.status == "pending"
        assert recovered_stage.attempt == 2

    execute_claim(claim)
    with get_session_factory()() as session:
        committed_counts = {
            table: session.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in (
                "plant_profiles",
                "editorial_reviews",
                "source_records",
                "plant_pipeline_items",
                "pipeline_botanical_reservations",
            )
        }
    execute_claim(claim)
    with get_session_factory()() as session:
        completed = get_current_run(session)
        profile = session.scalar(select(PlantProfile))
        assert completed is not None
        assert completed.status == "succeeded"
        assert completed.summary["completed_count"] == 1
        assert profile is not None and profile.status == "needs_review"
        assert session.scalar(select(func.count()).select_from(PlantProfile)) == 1
        assert session.scalar(select(func.count()).select_from(EditorialReview)) == 1
        assert {
            table: session.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in committed_counts
        } == committed_counts
        assert claim_recoverable_run(session) is None


def test_existing_names_synonyms_and_structured_discovery_subjects_block() -> None:
    catalog = load_plant_pipeline_catalog()
    base = catalog.candidates[0]
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        session.commit()

        scientific = base.model_copy(
            update={
                "accepted_scientific_name": "Matricaria chamomilla L.",
                "taxon_identifier": "new-taxon-1",
                "common_names": ["Different common name"],
                "synonyms": [],
            }
        )
        common = base.model_copy(
            update={
                "accepted_scientific_name": "New species",
                "taxon_identifier": "new-taxon-2",
                "common_names": ["  german\u2014chamomile "],
                "synonyms": [],
            }
        )
        synonym = base.model_copy(
            update={
                "accepted_scientific_name": "Another new species",
                "taxon_identifier": "new-taxon-3",
                "common_names": ["Another name"],
                "synonyms": ["MATRICARIA CHAMOMILLA L"],
            }
        )
        assert not check_candidate_eligibility(session, scientific).eligible
        assert not check_candidate_eligibility(session, common).eligible
        assert not check_candidate_eligibility(session, synonym).eligible

        record = session.scalar(select(SourceRecord).limit(1))
        assert record is not None
        session.add(
            DiscoveryEvent(
                source_record_id=record.id,
                status="relevant",
                category="research",
                relevance_confidence=1,
                reasons=["Explicit subject"],
                evidence_signals=[],
                detected_entities=[],
                evidence_package={
                    "botanical_identity": {
                        "accepted": True,
                        "accepted_scientific_name": base.accepted_scientific_name,
                        "taxon_identifier": base.taxon_identifier,
                        "synonyms": base.synonyms,
                        "common_name": base.common_names[0],
                    },
                    "incidental_prose": "Unrelated mention of a second herb.",
                },
            )
        )
        session.commit()
        assert not check_candidate_eligibility(session, base).eligible


def test_incidental_unstructured_prose_is_not_a_false_duplicate() -> None:
    base = load_plant_pipeline_catalog().candidates[0]
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        record = session.scalar(select(SourceRecord).limit(1))
        assert record is not None
        session.add(
            DiscoveryEvent(
                source_record_id=record.id,
                status="relevant",
                category="research",
                relevance_confidence=1,
                reasons=["Different represented subject"],
                evidence_signals=[],
                detected_entities=[],
                evidence_package={
                    "botanical_identity": {
                        "accepted": True,
                        "accepted_scientific_name": "Unrelated species",
                        "taxon_identifier": "unrelated-taxon",
                        "synonyms": [],
                        "common_name": "Unrelated plant",
                    },
                    "article_text": "Yarrow appears only in incidental prose.",
                },
            )
        )
        session.commit()
        assert check_candidate_eligibility(session, base).eligible


def test_expired_plant_run_completes_in_replacement_process_without_client() -> None:
    with get_session_factory()() as session:
        run = start_run(session, 1, str(uuid.uuid4()))
        run_id = run.id
        run.lease_expires_at = utc_now() - timedelta(seconds=1)
        session.commit()

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from backend.app.domains.pipeline.recovery import recover_once; "
            "assert recover_once()",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stderr
    with get_session_factory()() as session:
        recovered = session.get(PipelineRun, run_id)
        assert recovered is not None and recovered.status == "succeeded"
        assert session.scalar(select(func.count()).select_from(PlantProfile)) == 1
        assert session.scalar(select(func.count()).select_from(EditorialReview)) == 1
