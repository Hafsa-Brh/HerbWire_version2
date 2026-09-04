from datetime import datetime, timezone

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.discovery.corpus import (
    load_curated_discovery_corpus,
    load_final_discovery_corpus,
    load_new_plant_discovery_corpus,
)
from backend.app.domains.discovery.curated_import import import_curated_discoveries
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    EditorialReview,
    PlantProfile,
)
from sqlalchemy import select, text

TEST_LOGIN = {"email": "test-admin@example.invalid", "password": "test-password"}


@pytest.fixture(autouse=True)
def clean_catalog_tables():
    statement = text("""TRUNCATE discovery_article_plants, discovery_article_sources,
        editorial_reviews, discovery_articles, discovery_events, plant_profile_sources,
        plant_profile_revisions, plant_profiles, source_records, pipeline_stage_results,
        pipeline_runs, newsletter_subscriptions RESTART IDENTITY CASCADE""")
    with get_engine().begin() as connection:
        connection.execute(statement)
    yield
    with get_engine().begin() as connection:
        connection.execute(statement)


def _prepare_published_corpus() -> None:
    now = datetime.now(timezone.utc)
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        for profile in session.scalars(select(PlantProfile)).all():
            profile.status = "published"
            profile.published_at = profile.published_at or now
        session.flush()
        for corpus in (
            load_curated_discovery_corpus(),
            load_new_plant_discovery_corpus(),
            load_final_discovery_corpus(),
        ):
            import_curated_discoveries(session, corpus)
        for article in session.scalars(select(DiscoveryArticle)).all():
            article.status = "published"
            article.published_at = now
        for review in session.scalars(select(EditorialReview)).all():
            review.status = "approved"
        session.commit()


def _login(client) -> None:
    assert client.post("/api/v1/auth/login", json=TEST_LOGIN).status_code == 200


def test_content_catalog_is_authenticated_paginated_and_truthful(client) -> None:
    _prepare_published_corpus()
    assert client.get("/api/v1/admin/catalog/content").status_code == 401
    _login(client)

    response = client.get("/api/v1/admin/catalog/content?page=1&page_size=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == payload["summary"]["total_content"] == 60
    assert payload["summary"]["published_plants"] == 30
    assert payload["summary"]["published_discoveries"] == 30
    assert payload["summary"]["needs_review"] == 0
    assert len(payload["items"]) == 10
    assert payload["total_pages"] == 6
    assert {item["content_type"] for item in payload["items"]} <= {
        "plant_profile",
        "discovery",
    }
    assert all("run_id" not in item for item in payload["items"])
    assert all(item["public_path"].startswith(("/",)) for item in payload["items"])

    second_page = client.get("/api/v1/admin/catalog/content?page=2&page_size=10").json()
    assert {item["id"] for item in payload["items"]}.isdisjoint(
        {item["id"] for item in second_page["items"]}
    )
    final_page = client.get(
        "/api/v1/admin/catalog/content?page=999&page_size=10"
    ).json()
    assert final_page["page"] == final_page["total_pages"] == 6

    discoveries = client.get(
        "/api/v1/admin/catalog/content?content_type=discovery&page_size=50"
    ).json()
    assert discoveries["total"] == 30
    assert all(item["content_type"] == "discovery" for item in discoveries["items"])
    pmid = next(item["pmid"] for item in discoveries["items"] if item["pmid"])
    searched = client.get(f"/api/v1/admin/catalog/content?query={pmid}").json()
    assert searched["total"] == 1
    assert searched["items"][0]["pmid"] == pmid
    published = client.get(
        "/api/v1/admin/catalog/content?editorial_status=published&page_size=50"
    ).json()
    assert published["total"] == 60
    assert all(item["status"] == "published" for item in published["items"])


def test_source_catalog_exposes_links_without_sensitive_payloads(client) -> None:
    _prepare_published_corpus()
    assert client.get("/api/v1/admin/catalog/sources").status_code == 401
    _login(client)

    response = client.get("/api/v1/admin/catalog/sources?page=999&page_size=12")
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_count"] > 0
    assert payload["source_record_count"] >= payload["total"] > 0
    assert payload["page"] == payload["total_pages"]
    assert all(item["external_url"].startswith("https://") for item in payload["items"])
    serialized = response.text.lower()
    assert "permitted_extract" not in serialized
    assert "content_hash" not in serialized
    assert "database_url" not in serialized

    discoveries = client.get(
        "/api/v1/admin/catalog/sources?content_type=discovery&page_size=50"
    ).json()
    assert discoveries["total"] > 0
    assert all(
        any(link["content_type"] == "discovery" for link in item["associated_content"])
        for item in discoveries["items"]
    )
    sample = discoveries["items"][0]
    searched = client.get(
        f"/api/v1/admin/catalog/sources?query={sample['external_identifier']}"
    ).json()
    assert searched["total"] >= 1
    typed = client.get(
        f"/api/v1/admin/catalog/sources?source_type={sample['source_type']}"
    ).json()
    assert typed["total"] >= 1
    assert all(item["source_type"] == sample["source_type"] for item in typed["items"])
