import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.domains.pipeline.discovery_article_pipeline import (
    STAGES,
    DiscoveryPipelineBusyError,
    execute_run_to_terminal,
    get_current_run,
    start_run,
)
from backend.app.domains.pipeline.plant_profile_pipeline import (
    PlantPipelineBusyError,
)
from backend.app.domains.pipeline.plant_profile_pipeline import (
    start_run as start_plant_run,
)
from backend.app.domains.pipeline.recovery import (
    claim_recoverable_run,
    execute_claim,
)
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryPipelineItem,
    EditorialReview,
    PipelineRun,
    PlantPipelineItem,
    PlantProfile,
    SourceRecord,
    utc_now,
)
from sqlalchemy import func, select, text, update

LOGIN = {"email": "test-admin@example.invalid", "password": "test-password"}


@pytest.fixture(autouse=True)
def clean_discovery_pipeline_tables():
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "TRUNCATE discovery_pipeline_items, plant_pipeline_items, "
                "pipeline_stage_results, pipeline_runs, editorial_reviews, "
                "plant_profile_revisions, plant_profile_sources, "
                "discovery_article_plants, discovery_article_sources, "
                "discovery_articles, discovery_events, source_records, "
                "plant_profiles CASCADE"
            )
        )
        connection.execute(
            text("DELETE FROM sources WHERE identifier IN ('powo','ema','commons')")
        )
    yield
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "TRUNCATE discovery_pipeline_items, plant_pipeline_items, "
                "pipeline_stage_results, pipeline_runs, editorial_reviews, "
                "plant_profile_revisions, plant_profile_sources, "
                "discovery_article_plants, discovery_article_sources, "
                "discovery_articles, discovery_events, source_records, "
                "plant_profiles CASCADE"
            )
        )
        connection.execute(
            text("DELETE FROM sources WHERE identifier IN ('powo','ema','commons')")
        )


def seed_published_plants() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        session.execute(
            update(PlantProfile).values(
                status="published",
                published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            )
        )
        session.commit()


def test_discovery_batch_is_strictly_sequential_private_and_idempotent() -> None:
    seed_published_plants()
    key = str(uuid.uuid4())
    with get_session_factory()() as session:
        started = start_run(session, 2, key)
        run_id = started.id
        replay = start_run(session, 2, key)
        assert replay.id == run_id
        assert len(started.discovery_items) == 2
        assert all(item.status == "pending" for item in started.discovery_items)

        polled = get_current_run(session)
        assert polled is not None
        assert all(item.status == "pending" for item in polled.discovery_items)

    execute_run_to_terminal(run_id)

    with get_session_factory()() as session:
        completed = get_current_run(session)
        assert completed is not None
        assert completed.status == "succeeded"
        assert completed.summary["requested_count"] == 2
        assert completed.summary["planned_count"] == 2
        assert completed.summary["completed_count"] == 2
        assert completed.summary["held_count"] == 0
        assert completed.summary["failed_count"] == 0
        assert completed.summary["remaining_count"] == 0
        assert [stage.name for stage in completed.stages[: len(STAGES)]] == [
            name for name, _ in STAGES
        ]
        prior_completed = None
        for item in sorted(completed.discovery_items, key=lambda value: value.position):
            stages = sorted(
                [
                    stage
                    for stage in completed.stages
                    if stage.candidate_position == item.position
                ],
                key=lambda stage: [name for name, _ in STAGES].index(stage.name),
            )
            for earlier, later in zip(stages, stages[1:]):
                assert later.started_at >= earlier.completed_at
            if prior_completed is not None:
                assert item.started_at >= prior_completed
            prior_completed = item.completed_at
            assert item.discovery_article_id
            assert item.review_id
            assert item.source_count >= 1

        articles = list(session.scalars(select(DiscoveryArticle)))
        assert len(articles) == 2
        assert all(article.status == "needs_review" for article in articles)
        assert all(article.published_at is None for article in articles)
        assert (
            session.scalar(
                select(func.count())
                .select_from(EditorialReview)
                .where(EditorialReview.discovery_article_id.is_not(None))
            )
            == 2
        )
        assert session.scalar(select(func.count()).select_from(SourceRecord)) >= 2


def test_discovery_api_is_authenticated_bounded_and_redacted(client) -> None:
    seed_published_plants()
    assert client.get("/api/v1/admin/discovery-pipeline/preview").status_code == 401
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200
    for count in (0, 11):
        response = client.get(f"/api/v1/admin/discovery-pipeline/preview?count={count}")
        assert response.status_code == 422

    preview = client.get("/api/v1/admin/discovery-pipeline/preview?count=10").json()
    assert set(preview) == {"can_start", "unavailable_reason", "active_pipeline"}
    assert preview["can_start"] is True
    assert "candidate" not in str(preview).casefold()


def test_cross_pipeline_global_exclusivity_and_domain_reservations() -> None:
    seed_published_plants()
    with get_session_factory()() as session:
        plant = start_plant_run(session, 1, str(uuid.uuid4()))
        assert plant.status == "running"
    with get_session_factory()() as session:
        with pytest.raises(DiscoveryPipelineBusyError):
            start_run(session, 1, str(uuid.uuid4()))
        assert (
            session.scalar(select(func.count()).select_from(DiscoveryPipelineItem)) == 0
        )


def test_discovery_active_blocks_plant_launch_without_cross_reservation() -> None:
    seed_published_plants()
    with get_session_factory()() as session:
        discovery = start_run(session, 1, str(uuid.uuid4()))
        assert discovery.status == "running"
    with get_session_factory()() as session:
        with pytest.raises(PlantPipelineBusyError):
            start_plant_run(session, 1, str(uuid.uuid4()))
        assert session.scalar(select(func.count()).select_from(PlantPipelineItem)) == 0


def test_stale_discovery_run_recovers_automatically_at_same_boundary() -> None:
    seed_published_plants()
    with get_session_factory()() as session:
        run = start_run(session, 1, str(uuid.uuid4()))
        item = run.discovery_items[0]
        first_stage = next(
            stage
            for stage in run.stages
            if stage.candidate_position == 1 and stage.name == STAGES[0][0]
        )
        item.status = "running"
        first_stage.status = "running"
        first_stage.started_at = utc_now() - timedelta(minutes=3)
        run.lease_expires_at = utc_now() + timedelta(minutes=1)
        run_id = run.id
        session.commit()
        assert claim_recoverable_run(session) is None
        run.lease_expires_at = utc_now() - timedelta(seconds=1)
        session.commit()
        claim = claim_recoverable_run(session)
        assert claim is not None and claim.run_id == run_id
        recovered = get_current_run(session)
        retry_stage = next(
            stage
            for stage in recovered.stages
            if stage.candidate_position == 1 and stage.name == STAGES[0][0]
        )
        assert retry_stage.attempt == 2
        assert retry_stage.status == "pending"

    execute_claim(claim)
    with get_session_factory()() as session:
        committed_counts = {
            table: session.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in (
                "discovery_articles",
                "discovery_events",
                "discovery_article_sources",
                "editorial_reviews",
                "source_records",
                "discovery_pipeline_items",
                "pipeline_botanical_reservations",
            )
        }
    execute_claim(claim)
    with get_session_factory()() as session:
        completed = session.get(PipelineRun, run_id)
        article = session.scalar(select(DiscoveryArticle))
        assert completed is not None
        assert completed.status == "succeeded"
        assert article is not None and article.status == "needs_review"
        assert session.scalar(select(func.count()).select_from(DiscoveryArticle)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(EditorialReview)
                .where(EditorialReview.discovery_article_id == article.id)
            )
            == 1
        )
        assert {
            table: session.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in committed_counts
        } == committed_counts


def test_duplicate_pubmed_and_doi_are_ineligible() -> None:
    seed_published_plants()
    with get_session_factory()() as session:
        run = start_run(session, 1, str(uuid.uuid4()))
        run_id = run.id
    execute_run_to_terminal(run_id)
    with get_session_factory()() as session:
        second = start_run(
            session,
            1,
            str(uuid.uuid4()),
            all_available=True,
        )
        assert second.summary["available_count_at_start"] == 19
        assert len(second.discovery_items) == 9
        existing = session.scalar(
            select(SourceRecord).where(SourceRecord.doi.is_not(None))
        )
        assert existing is not None
        assert existing.external_identifier == "41473738"


def test_expired_discovery_run_recovers_in_replacement_process() -> None:
    seed_published_plants()
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
        article = session.scalar(select(DiscoveryArticle))
        assert recovered is not None and recovered.status == "succeeded"
        assert article is not None and article.status == "needs_review"
        assert (
            session.scalar(
                select(func.count())
                .select_from(EditorialReview)
                .where(EditorialReview.discovery_article_id == article.id)
            )
            == 1
        )
