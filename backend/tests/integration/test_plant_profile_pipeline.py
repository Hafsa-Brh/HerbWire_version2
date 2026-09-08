import uuid
from datetime import datetime, timezone

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.domains.pipeline.plant_profile_pipeline import (
    execute_run_to_terminal,
    get_run,
    preview_candidates,
    start_run,
)
from backend.app.models.encyclopedia import (
    EditorialReview,
    PipelineBotanicalReservation,
    PipelineRun,
    PlantPipelineItem,
    PlantProfile,
)
from sqlalchemy import func, select, text, update

LOGIN = {"email": "test-admin@example.invalid", "password": "test-password"}


@pytest.fixture(autouse=True)
def clean_pipeline_tables():
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "TRUNCATE pipeline_botanical_reservations, plant_pipeline_items, "
                "discovery_pipeline_items, pipeline_stage_results, pipeline_runs, "
                "editorial_reviews, plant_profile_revisions, plant_profile_sources, "
                "discovery_article_plants, discovery_article_sources, "
                "discovery_articles, discovery_events, source_records, "
                "plant_profiles CASCADE"
            )
        )
        connection.execute(
            text("DELETE FROM sources WHERE identifier IN ('powo','ema','commons')")
        )
    yield


def login(client) -> None:
    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200


@pytest.mark.parametrize("count", [1, 2, 3])
def test_requested_count_runs_in_background_and_persists_exact_batch(client, count):
    login(client)
    started = client.post(
        "/api/v1/admin/plant-pipeline/runs",
        json={"count": count, "idempotency_key": str(uuid.uuid4())},
    )
    assert started.status_code == 201
    assert set(started.json()) == {"id", "status", "items"}
    completed = client.get(
        f"/api/v1/admin/plant-pipeline/runs/{started.json()['id']}"
    ).json()
    assert completed["status"] == "succeeded"
    assert len(completed["items"]) == count
    assert len({item["title"] for item in completed["items"]}) == count
    with get_session_factory()() as session:
        run = get_run(session, uuid.UUID(completed["id"]))
        assert run is not None
        assert run.summary["requested_count"] == count
        assert run.summary["planned_count"] == count
        assert run.summary["completed_count"] == count
        prior_completed = None
        for item in sorted(run.plant_items, key=lambda value: value.position):
            stages = sorted(
                (
                    stage
                    for stage in run.stages
                    if stage.candidate_position == item.position
                ),
                key=lambda value: value.started_at,
            )
            assert all(
                a.completed_at <= b.started_at for a, b in zip(stages, stages[1:])
            )
            if prior_completed is not None:
                assert prior_completed <= item.started_at
            prior_completed = item.completed_at
            assert item.review_id is not None
        assert (
            session.scalar(
                select(func.count())
                .select_from(PlantProfile)
                .where(PlantProfile.status == "published")
            )
            == 0
        )


def test_full_ten_item_batch_leaves_protected_ten_and_rejection_is_zero_write():
    with get_session_factory()() as session:
        first = start_run(session, 5, str(uuid.uuid4()))
        first_id, first_owner = first.id, first.lease_owner
    execute_run_to_terminal(first_id, first_owner)
    with get_session_factory()() as session:
        assert preview_candidates(session, 10)["available_count"] == 20
        run = start_run(session, 10, str(uuid.uuid4()))
        run_id, owner = run.id, run.lease_owner
    execute_run_to_terminal(run_id, owner)
    with get_session_factory()() as session:
        remaining = preview_candidates(session, 1)
        assert remaining["available_count"] == 10
        assert remaining["can_start"] is False
        before = (
            session.scalar(select(func.count()).select_from(PipelineRun)),
            session.scalar(select(func.count()).select_from(PlantPipelineItem)),
            session.scalar(
                select(func.count()).select_from(PipelineBotanicalReservation)
            ),
            session.scalar(select(func.count()).select_from(EditorialReview)),
        )
        with pytest.raises(ValueError, match="protected editorial reserve"):
            start_run(session, 1, str(uuid.uuid4()))
        after = (
            session.scalar(select(func.count()).select_from(PipelineRun)),
            session.scalar(select(func.count()).select_from(PlantPipelineItem)),
            session.scalar(
                select(func.count()).select_from(PipelineBotanicalReservation)
            ),
            session.scalar(select(func.count()).select_from(EditorialReview)),
        )
        assert after == before


def test_api_capacity_is_redacted_and_public_drafts_remain_private(client):
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        session.execute(
            update(PlantProfile).values(
                status="published",
                published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            )
        )
        session.commit()
    assert client.get("/api/v1/admin/plant-pipeline/preview").status_code == 401
    login(client)
    preview = client.get("/api/v1/admin/plant-pipeline/preview?count=10").json()
    assert set(preview) == {"can_start", "unavailable_reason", "active_pipeline"}
    serialized = str(preview).casefold()
    assert "candidate" not in serialized and "taxon" not in serialized
    key = str(uuid.uuid4())
    first = client.post(
        "/api/v1/admin/plant-pipeline/runs", json={"count": 1, "idempotency_key": key}
    )
    replay = client.post(
        "/api/v1/admin/plant-pipeline/runs", json={"count": 1, "idempotency_key": key}
    )
    assert replay.json()["id"] == first.json()["id"]
    assert client.get("/api/v1/plants?page_size=50").json()["total"] == 30
