from copy import deepcopy

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.discovery.corpus import load_curated_discovery_corpus
from backend.app.domains.discovery.curated_import import import_curated_discoveries
from backend.app.domains.discovery.service import (
    decide_discovery_article,
    get_discovery_article,
    publish_discovery_article,
)
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    EditorialReview,
    PlantProfile,
)
from sqlalchemy import func, select, text

TEST_LOGIN = {"email": "test-admin@example.invalid", "password": "test-password"}


@pytest.fixture(autouse=True)
def clean_database():
    statement = text("""TRUNCATE discovery_article_plants, discovery_article_sources,
        editorial_reviews, discovery_articles, discovery_events, plant_profile_sources,
        plant_profile_revisions, plant_profiles, source_records, pipeline_stage_results,
        pipeline_runs, newsletter_subscriptions RESTART IDENTITY CASCADE""")
    with get_engine().begin() as connection:
        connection.execute(statement)
        connection.execute(
            text("DELETE FROM sources WHERE identifier <> 'pubmed-eutils'")
        )
    yield
    with get_engine().begin() as connection:
        connection.execute(statement)
        connection.execute(
            text("DELETE FROM sources WHERE identifier <> 'pubmed-eutils'")
        )


def _prepare() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        for profile in session.scalars(select(PlantProfile)).all():
            profile.status = "published"
        session.commit()


def _login(client) -> None:
    assert client.post("/api/v1/auth/login", json=TEST_LOGIN).status_code == 200


def test_import_is_idempotent_and_keeps_media_separate_from_sources() -> None:
    _prepare()
    corpus = load_curated_discovery_corpus()
    with get_session_factory()() as session:
        first = import_curated_discoveries(session, corpus)
        second = import_curated_discoveries(session, corpus)
        articles = list(session.scalars(select(DiscoveryArticle)).all())
        reviews = session.scalar(
            select(func.count())
            .select_from(EditorialReview)
            .where(EditorialReview.discovery_article_id.is_not(None))
        )
    assert first.created == first.reviews_created == first.source_records_created == 10
    assert second.created == 0 and second.unchanged == 10
    assert len(articles) == reviews == 10
    assert all(article.status == "needs_review" for article in articles)
    assert all(article.published_at is None for article in articles)
    assert all(article.content_origin == "curated" for article in articles)
    assert all(
        article.hero_image["license"] and article.hero_image["checksum_sha256"]
        for article in articles
    )


def test_import_rejects_changed_same_version_without_writes() -> None:
    _prepare()
    corpus = load_curated_discovery_corpus()
    with get_session_factory()() as session:
        import_curated_discoveries(session, corpus)
        changed = deepcopy(corpus)
        changed.articles[0].headline += " changed"
        changed.articles[0].content_checksum = changed.articles[0].calculated_checksum()
        with pytest.raises(ValueError, match="changed same-version"):
            import_curated_discoveries(session, changed)
        assert session.scalar(select(func.count()).select_from(DiscoveryArticle)) == 10


def test_approval_and_publication_are_separate_and_synthetic_is_blocked(client) -> None:
    _prepare()
    with get_session_factory()() as session:
        import_curated_discoveries(session, load_curated_discovery_corpus())
        article = session.scalar(
            select(DiscoveryArticle).order_by(DiscoveryArticle.slug)
        )
        assert article is not None
        article_id = article.id
    assert client.get("/api/v1/discoveries").json()["total"] == 0
    assert (
        client.post(
            f"/api/v1/admin/discovery/reviews/{article_id}/approve",
            json={"reviewer_name": "Editor"},
        ).status_code
        == 401
    )
    _login(client)
    approved = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/approve",
        json={"reviewer_name": "Editor"},
    )
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert client.get("/api/v1/discoveries").json()["total"] == 0
    published = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/publish",
        json={"reviewer_name": "Editor"},
    )
    assert published.status_code == 200 and published.json()["status"] == "published"
    assert (
        client.post(
            f"/api/v1/admin/discovery/reviews/{article_id}/publish",
            json={"reviewer_name": "Editor"},
        ).status_code
        == 200
    )
    public = client.get("/api/v1/discoveries").json()
    assert public["total"] == 1
    assert public["items"][0]["linked_plants"]
    assert "qa_payload" not in public["items"][0]

    with get_session_factory()() as session:
        synthetic = session.scalar(
            select(DiscoveryArticle).where(DiscoveryArticle.id != article_id)
        )
        assert synthetic is not None
        synthetic.content_origin = "synthetic"
        synthetic.status = "approved"
        synthetic.reviews[0].status = "approved"
        session.commit()
        synthetic_id = synthetic.id
    blocked = client.post(
        f"/api/v1/admin/discovery/reviews/{synthetic_id}/publish",
        json={"reviewer_name": "Editor"},
    )
    assert blocked.status_code == 409
    assert client.get("/api/v1/discoveries").json()["total"] == 1


def test_publication_commit_failure_rolls_back(monkeypatch) -> None:
    _prepare()
    with get_session_factory()() as session:
        import_curated_discoveries(session, load_curated_discovery_corpus())
        article = session.scalar(
            select(DiscoveryArticle).order_by(DiscoveryArticle.slug)
        )
        assert article is not None
        decide_discovery_article(session, article.id, "approved", "Editor", None)
        original_commit = session.commit

        def fail_commit() -> None:
            raise RuntimeError("simulated commit failure")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="simulated commit failure"):
            publish_discovery_article(session, article.id, "Editor")
        monkeypatch.setattr(session, "commit", original_commit)
        stored = get_discovery_article(session, article.id)
        assert stored is not None
        assert stored.status == "approved"
        assert stored.published_at is None
