from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from backend.app.api.routes.discovery_editorial import get_pubmed_provider
from backend.app.collectors.providers.base import CollectionRequest
from backend.app.collectors.providers.pubmed import (
    PubMedCollectionProvider,
    PubMedProviderConfig,
    PubMedTransientError,
)
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.discovery.service import (
    DISCOVERY_STAGES,
    run_discovery_pipeline,
)
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.main import app
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryEvent,
    EditorialReview,
    PipelineRun,
    SourceRecord,
)
from backend.app.workers.run_pubmed_discovery import SavedPubMedTransport
from sqlalchemy import func, select, text

FIXTURES = Path(__file__).parents[1] / "fixtures" / "pubmed"
TEST_LOGIN = {"email": "test-admin@example.invalid", "password": "test-password"}
REQUEST = CollectionRequest(date(2026, 8, 1), date(2026, 9, 1), 1)


def fixture_provider() -> PubMedCollectionProvider:
    return PubMedCollectionProvider(
        PubMedProviderConfig(
            email="fixture-test@example.invalid",
            minimum_request_interval_seconds=0,
        ),
        transport=SavedPubMedTransport(FIXTURES),
    )


@pytest.fixture(autouse=True)
def clean_discovery_database():
    statement = text(
        """TRUNCATE discovery_article_sources, editorial_reviews,
        discovery_articles, discovery_events, plant_profile_sources,
        plant_profile_revisions, plant_profiles, source_records,
        pipeline_stage_results, pipeline_runs, newsletter_subscriptions
        RESTART IDENTITY CASCADE"""
    )
    with get_engine().begin() as connection:
        connection.execute(statement)
        connection.execute(
            text("DELETE FROM sources WHERE identifier <> 'pubmed-eutils'")
        )
    yield
    app.dependency_overrides.pop(get_pubmed_provider, None)
    with get_engine().begin() as connection:
        connection.execute(statement)
        connection.execute(
            text("DELETE FROM sources WHERE identifier <> 'pubmed-eutils'")
        )


def login(client) -> None:
    response = client.post("/api/v1/auth/login", json=TEST_LOGIN)
    assert response.status_code == 200


def scalar_count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_pipeline_creates_one_private_traceable_review_and_is_idempotent() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        first = run_discovery_pipeline(session, REQUEST, fixture_provider())
        first_id = first.id
        second = run_discovery_pipeline(session, REQUEST, fixture_provider())
        original = fixture_provider().collect(REQUEST)[0]

        class OneRecordProvider:
            name = "pubmed"

            def __init__(self, record):
                self.record = record

            def collect(self, request=None):
                return [self.record]

        doi_duplicate = run_discovery_pipeline(
            session,
            CollectionRequest(date(2026, 8, 2), date(2026, 9, 1), 1),
            OneRecordProvider(
                replace(
                    original,
                    external_identifier="49900001",
                    url="https://pubmed.ncbi.nlm.nih.gov/49900001/",
                    canonical_url="https://pubmed.ncbi.nlm.nih.gov/49900001/",
                    title=f"{original.title} updated",
                )
            ),
        )
        url_duplicate = run_discovery_pipeline(
            session,
            CollectionRequest(date(2026, 8, 3), date(2026, 9, 1), 1),
            OneRecordProvider(
                replace(
                    original,
                    external_identifier="49900002",
                    doi=None,
                    title=f"{original.title} revised",
                )
            ),
        )
        hash_duplicate = run_discovery_pipeline(
            session,
            CollectionRequest(date(2026, 8, 4), date(2026, 9, 1), 1),
            OneRecordProvider(
                replace(
                    original,
                    external_identifier="49900003",
                    doi=None,
                    url="https://pubmed.ncbi.nlm.nih.gov/49900003/",
                    canonical_url="https://pubmed.ncbi.nlm.nih.gov/49900003/",
                )
            ),
        )

        assert first.status == "succeeded"
        assert [stage.name for stage in first.stages] == list(DISCOVERY_STAGES)
        assert all(stage.status in {"succeeded", "skipped"} for stage in first.stages)
        assert first.summary["review_ready"] == 1
        assert first.summary["auto_published"] == 0
        assert second.id == first_id
        assert doi_duplicate.id != first_id
        assert all(
            run.summary["records_duplicate"] == 1
            for run in (doi_duplicate, url_duplicate, hash_duplicate)
        )
        assert scalar_count(session, SourceRecord) == 94
        assert scalar_count(session, DiscoveryEvent) == 1
        assert scalar_count(session, DiscoveryArticle) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(EditorialReview)
                .where(EditorialReview.discovery_article_id.is_not(None))
            )
            == 1
        )
        article = session.scalar(select(DiscoveryArticle))
        assert article is not None
        assert article.status == "needs_review"
        assert article.published_at is None
        assert article.sources[0].source_record.external_identifier == "39900001"
        assert article.event.evidence_package["excerpts"][0]["location"].startswith(
            "abstract_sentence:"
        )


def test_failed_stage_is_visible_and_retry_reuses_run_without_duplicates() -> None:
    class FailingProvider:
        name = "pubmed"

        def collect(self, request=None):
            raise PubMedTransientError("pubmed_transport_error", "Safe timeout.")

    with get_session_factory()() as session:
        seed_curated_profiles(session)
        failed = run_discovery_pipeline(session, REQUEST, FailingProvider())
        assert failed.status == "failed"
        assert failed.summary["failed_stage"] == "collect"
        assert failed.stages[0].error_code == "pubmed_transport_error"
        assert "Safe timeout" in (failed.stages[0].error_message or "")

        recovered = run_discovery_pipeline(session, REQUEST, fixture_provider())
        assert recovered.id == failed.id
        assert recovered.status == "succeeded"
        assert recovered.summary["retry_count"] == 1
        collect_stage = next(
            stage for stage in recovered.stages if stage.name == "collect"
        )
        assert collect_stage.attempt == 2
        assert scalar_count(session, DiscoveryArticle) == 1


def test_authenticated_trigger_validation_and_public_private_separation(client) -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
    app.dependency_overrides[get_pubmed_provider] = fixture_provider

    payload = {
        "source": "pubmed",
        "start_date": "2026-08-01",
        "end_date": "2026-09-01",
        "max_records": 1,
    }
    assert client.post("/api/v1/admin/discovery/runs", json=payload).status_code == 401
    login(client)
    accepted = client.post("/api/v1/admin/discovery/runs", json=payload)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "succeeded"
    assert accepted.json()["summary"]["review_ready"] == 1

    too_many = client.post(
        "/api/v1/admin/discovery/runs", json={**payload, "max_records": 6}
    )
    too_wide = client.post(
        "/api/v1/admin/discovery/runs",
        json={**payload, "start_date": "2026-01-01"},
    )
    arbitrary = client.post(
        "/api/v1/admin/discovery/runs",
        json={**payload, "url": "https://example.invalid", "command": "whoami"},
    )
    assert too_many.status_code == 422
    assert too_wide.status_code == 422
    assert arbitrary.status_code == 422
    assert "whoami" not in accepted.text

    queue = client.get("/api/v1/admin/discovery/reviews")
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    article = queue.json()["items"][0]
    assert article["status"] == "needs_review"
    assert article["sources"][0]["pmid"] == "39900001"
    assert client.get("/api/v1/discoveries").json()["total"] == 0
    assert client.get(f"/api/v1/discoveries/{article['slug']}").status_code == 404

    approved = client.post(
        f"/api/v1/admin/discovery/reviews/{article['id']}/approve",
        json={"reviewer_name": "Test editor"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert client.get("/api/v1/discoveries").json()["total"] == 0
    with get_session_factory()() as session:
        stored = session.get_one(DiscoveryArticle, article["id"])
        stored.status = "published"
        stored.published_at = datetime.now(timezone.utc)
        session.commit()
    public_item = client.get("/api/v1/discoveries").json()["items"][0]
    assert public_item["headline"] == article["headline"]
    assert "qa_payload" not in public_item
    assert "reviewer_name" not in public_item
    assert "detected_entities" not in public_item


def test_hold_and_reject_require_reason_and_never_publish(client) -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        run_discovery_pipeline(session, REQUEST, fixture_provider())
        article_id = session.scalar(select(DiscoveryArticle.id))
    login(client)
    with get_session_factory()() as session:
        article = session.get_one(DiscoveryArticle, article_id)
        article.qa_payload = {"passed": False}
        session.commit()
    blocked_approval = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/approve",
        json={"reviewer_name": "Test editor"},
    )
    assert blocked_approval.status_code == 409

    missing_reason = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/hold",
        json={"reviewer_name": "Test editor"},
    )
    assert missing_reason.status_code == 409
    held = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/hold",
        json={"reviewer_name": "Test editor", "reason": "Needs methods review."},
    )
    rejected = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/reject",
        json={"reviewer_name": "Test editor", "reason": "Not sufficiently supported."},
    )
    assert held.status_code == 200
    assert held.json()["status"] == "held"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert client.get("/api/v1/discoveries").json()["total"] == 0
    with get_session_factory()() as session:
        article = session.get_one(DiscoveryArticle, article_id)
        assert article.published_at is None
        assert article.reviewed_at.tzinfo is not None
        run = session.scalar(select(PipelineRun))
        assert run is not None and run.finished_at.tzinfo is not None
