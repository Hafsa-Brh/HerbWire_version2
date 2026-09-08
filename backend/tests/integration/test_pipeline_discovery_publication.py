import uuid
from datetime import datetime, timezone

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.domains.pipeline.discovery_article_pipeline import (
    execute_run_to_terminal,
    start_run,
)
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    DiscoveryPipelineItem,
    EditorialReview,
    PlantProfile,
)
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

LOGIN = {"email": "test-admin@example.invalid", "password": "test-password"}


@pytest.fixture(autouse=True)
def clean_pipeline_publication_tables():
    statement = text(
        "TRUNCATE discovery_pipeline_items, plant_pipeline_items, "
        "pipeline_stage_results, pipeline_runs, editorial_reviews, "
        "plant_profile_revisions, plant_profile_sources, "
        "discovery_article_plants, discovery_article_sources, "
        "discovery_articles, discovery_events, source_records, "
        "plant_profiles CASCADE"
    )
    with get_engine().begin() as connection:
        connection.execute(statement)
        connection.execute(
            text("DELETE FROM sources WHERE identifier IN ('powo','ema','commons')")
        )
    yield
    with get_engine().begin() as connection:
        connection.execute(statement)
        connection.execute(
            text("DELETE FROM sources WHERE identifier IN ('powo','ema','commons')")
        )


def _seed_published_plants() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        session.execute(
            update(PlantProfile).values(
                status="published",
                published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            )
        )
        session.commit()


def test_pipeline_discovery_approve_publish_is_private_then_idempotent(client) -> None:
    _seed_published_plants()
    with get_session_factory()() as session:
        run = start_run(session, 1, str(uuid.uuid4()))
        run_id = run.id
    execute_run_to_terminal(run_id)

    with get_session_factory()() as session:
        article = session.scalar(select(DiscoveryArticle))
        assert article is not None
        article_id = article.id
        slug = article.slug
        preserved_sources = session.scalar(
            text(
                "SELECT count(*) FROM discovery_article_sources "
                "WHERE discovery_article_id=:article_id"
            ),
            {"article_id": article_id},
        )
        preserved_links = session.scalar(
            text(
                "SELECT count(*) FROM discovery_article_plants "
                "WHERE discovery_article_id=:article_id"
            ),
            {"article_id": article_id},
        )
        preserved_geography = list(article.geography)
        preserved_media = dict(article.hero_image)
        item = session.scalar(
            select(DiscoveryPipelineItem).where(
                DiscoveryPipelineItem.discovery_article_id == article_id
            )
        )
        assert item is not None and item.status == "succeeded"
        assert article.status == "needs_review"
        assert article.published_at is None

    assert client.get(f"/api/v1/discoveries/{slug}").status_code == 404
    public_before = client.get("/api/v1/discoveries?page=1&page_size=12")
    assert public_before.status_code == 200
    assert all(item["id"] != str(article_id) for item in public_before.json()["items"])

    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200
    unapproved = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/publish",
        json={"reviewer_name": "Pipeline publication test"},
    )
    assert unapproved.status_code == 409
    assert "explicitly approved first" in unapproved.json()["detail"]
    approved = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/approve",
        json={"reviewer_name": "Pipeline publication test"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["published_at"] is None
    assert client.get(f"/api/v1/discoveries/{slug}").status_code == 404

    published = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/publish",
        json={"reviewer_name": "Pipeline publication test"},
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None

    replay = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/publish",
        json={"reviewer_name": "Pipeline publication test"},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == str(article_id)

    public_after = client.get("/api/v1/discoveries?page=1&page_size=12")
    assert public_after.status_code == 200
    assert public_after.json()["items"][0]["id"] == str(article_id)
    assert client.get(f"/api/v1/discoveries/{slug}").status_code == 200

    with get_session_factory()() as session:
        stored = session.get(DiscoveryArticle, article_id)
        assert stored is not None and stored.status == "published"
        assert stored.published_at is not None
        assert session.scalar(select(func.count()).select_from(DiscoveryArticle)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(EditorialReview)
                .where(EditorialReview.discovery_article_id == article_id)
            )
            == 1
        )
        assert (
            session.scalar(
                text(
                    "SELECT count(*) FROM discovery_article_sources "
                    "WHERE discovery_article_id=:article_id"
                ),
                {"article_id": article_id},
            )
            == preserved_sources
        )
        assert (
            session.scalar(
                text(
                    "SELECT count(*) FROM discovery_article_plants "
                    "WHERE discovery_article_id=:article_id"
                ),
                {"article_id": article_id},
            )
            == preserved_links
        )
        assert stored.geography == preserved_geography
        assert stored.hero_image == preserved_media


def test_external_botanical_identity_blocks_pipeline_publication(client) -> None:
    _seed_published_plants()
    with get_session_factory()() as session:
        run = start_run(session, 1, str(uuid.uuid4()))
        run_id = run.id
    execute_run_to_terminal(run_id)

    with get_session_factory()() as session:
        article = session.scalar(select(DiscoveryArticle))
        assert article is not None
        article_id = article.id
        identity = article.event.evidence_package["botanical_identity"]
        conflicting_profile = session.scalar(select(PlantProfile).limit(1))
        assert conflicting_profile is not None
        conflicting_profile.taxon_identifier = identity["authority_taxon_id"]
        conflicting_profile.accepted_scientific_name = identity[
            "accepted_scientific_name"
        ]
        conflicting_profile.botanical_author = identity.get("botanical_author", "")
        conflicting_profile.known_synonyms = identity.get("synonyms", [])
        conflicting_profile.display_common_name = identity["common_name"]
        session.commit()

    assert client.post("/api/v1/auth/login", json=LOGIN).status_code == 200
    assert (
        client.post(
            f"/api/v1/admin/discovery/reviews/{article_id}/approve",
            json={"reviewer_name": "Pipeline publication test"},
        ).status_code
        == 200
    )
    blocked = client.post(
        f"/api/v1/admin/discovery/reviews/{article_id}/publish",
        json={"reviewer_name": "Pipeline publication test"},
    )
    assert blocked.status_code == 409
    assert "already represented or reserved" in blocked.json()["detail"]

    with get_session_factory()() as session:
        stored = session.get(DiscoveryArticle, article_id)
        assert stored is not None
        assert stored.status == "approved"
        assert stored.published_at is None
        assert (
            session.scalar(
                select(func.count())
                .select_from(DiscoveryArticle)
                .where(DiscoveryArticle.status == "published")
            )
            == 0
        )


def test_different_candidate_cannot_reserve_the_same_taxon() -> None:
    _seed_published_plants()
    with get_session_factory()() as session:
        run = start_run(session, 1, str(uuid.uuid4()))
        run_id = run.id
    execute_run_to_terminal(run_id)

    with get_session_factory()() as session:
        own = session.execute(
            text(
                "SELECT pipeline_run_id, identity_key "
                "FROM pipeline_botanical_reservations LIMIT 1"
            )
        ).one()
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO pipeline_botanical_reservations "
                    "(id,pipeline_run_id,domain,candidate_key,identity_key,created_at) "
                    "VALUES (:id,:run_id,'discoveries','different-candidate',"
                    ":identity_key,now())"
                ),
                {
                    "id": uuid.uuid4(),
                    "run_id": own.pipeline_run_id,
                    "identity_key": own.identity_key,
                },
            )
        session.rollback()

    with get_session_factory()() as session:
        assert (
            session.scalar(
                text(
                    "SELECT count(*) FROM pipeline_botanical_reservations "
                    "WHERE identity_key=:identity_key"
                ),
                {"identity_key": own.identity_key},
            )
            == 1
        )
