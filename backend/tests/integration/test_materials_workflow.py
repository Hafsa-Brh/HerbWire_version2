from copy import deepcopy

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.materials.corpus import load_curated_material_corpus
from backend.app.domains.materials.curated_import import import_curated_materials
from backend.app.models.materials import MaterialStory, MaterialStorySource
from sqlalchemy import func, select, text


@pytest.fixture(autouse=True)
def clean_material_tables():
    statement = text(
        "TRUNCATE material_story_sources, material_stories RESTART IDENTITY CASCADE"
    )

    def clean() -> None:
        with get_engine().begin() as connection:
            connection.execute(statement)
            connection.execute(
                text(
                    "DELETE FROM source_records WHERE supports ->> 'materials' = 'true'"
                )
            )
            connection.execute(
                text(
                    "DELETE FROM sources WHERE identifier <> 'pubmed-eutils' "
                    "AND id NOT IN (SELECT DISTINCT source_id FROM source_records)"
                )
            )

    clean()
    yield
    clean()


def test_material_import_is_idempotent_and_rejects_same_version_changes() -> None:
    corpus = load_curated_material_corpus()
    expected_links = sum(len(story.sources) for story in corpus.stories)

    with get_session_factory()() as session:
        first = import_curated_materials(session, corpus)
        second = import_curated_materials(session, corpus)
        assert first.created == 7
        assert first.source_links_created == expected_links
        assert second.created == 0
        assert second.unchanged == 7
        assert session.scalar(select(func.count()).select_from(MaterialStory)) == 7
        assert (
            session.scalar(select(func.count()).select_from(MaterialStorySource))
            == expected_links
        )

        changed = deepcopy(corpus)
        changed.stories[0].title += " altered"
        with pytest.raises(ValueError, match="changed same-version"):
            import_curated_materials(session, changed)
        assert session.scalar(select(func.count()).select_from(MaterialStory)) == 7


def test_material_public_api_lists_filters_details_and_404s(client) -> None:
    with get_session_factory()() as session:
        import_curated_materials(session, load_curated_material_corpus())

    response = client.get("/api/v1/materials?page=1&page_size=3")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 7
    assert payload["page"] == 1
    assert payload["page_size"] == 3
    assert payload["total_pages"] == 3
    assert len(payload["items"]) == 3
    assert payload["items"][0]["featured"] is True

    final_page = client.get("/api/v1/materials?page=99&page_size=3").json()
    assert final_page["page"] == 3
    category = payload["items"][0]["category"]
    filtered = client.get(
        "/api/v1/materials", params={"category": category, "page_size": 50}
    ).json()
    assert filtered["total"] >= 1
    assert all(item["category"] == category for item in filtered["items"])

    story = payload["items"][0]
    detail = client.get(f"/api/v1/materials/{story['slug']}")
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["sections"]) >= 6
    assert len(body["sources"]) >= 2
    assert all(source["supported_sections"] for source in body["sources"])
    assert client.get("/api/v1/admin/catalog/content").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "test-admin@example.invalid", "password": "test-password"},
        ).status_code
        == 200
    )
    catalogue = client.get(
        "/api/v1/admin/catalog/content",
        params={"content_type": "material_story", "page_size": 50},
    ).json()
    assert catalogue["total"] == 7
    assert catalogue["summary"]["published_materials"] == 7
    assert all(item["content_type"] == "material_story" for item in catalogue["items"])
    sources = client.get(
        "/api/v1/admin/catalog/sources",
        params={"content_type": "material_story", "page_size": 50},
    ).json()
    assert sources["total"] >= 14
    assert all(
        any(
            link["content_type"] == "material_story"
            for link in item["associated_content"]
        )
        for item in sources["items"]
    )
    serialized = detail.text.lower()
    assert "database_url" not in serialized
    assert "content_hash" not in serialized
    assert client.get("/api/v1/materials/not-a-story").status_code == 404
