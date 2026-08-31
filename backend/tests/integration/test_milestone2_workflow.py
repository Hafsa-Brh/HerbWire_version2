import uuid
from datetime import datetime, timezone

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.domains.pipeline.fixture_pipeline import run_fixture_pipeline
from backend.app.models.encyclopedia import (
    EditorialReview,
    NewsletterSubscription,
    PlantProfile,
    PlantProfileRevision,
    SourceRecord,
)
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

TEST_LOGIN = {"email": "test-admin@example.invalid", "password": "test-password"}


@pytest.fixture(autouse=True)
def clean_milestone2_tables():
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM newsletter_subscriptions"))
        connection.execute(text("DELETE FROM pipeline_stage_results"))
        connection.execute(text("DELETE FROM pipeline_runs"))
        connection.execute(text("DELETE FROM editorial_reviews"))
        connection.execute(text("DELETE FROM plant_profile_revisions"))
        connection.execute(text("DELETE FROM plant_profile_sources"))
        connection.execute(text("DELETE FROM plant_profiles"))
        connection.execute(text("DELETE FROM source_records"))
        connection.execute(
            text(
                """
                DELETE FROM sources
                WHERE identifier in (
                    'kew-powo', 'ema-herbal', 'nccih', 'wikimedia-commons',
                    'fixture-discovery'
                )
                """
            )
        )
    yield
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM newsletter_subscriptions"))
        connection.execute(text("DELETE FROM pipeline_stage_results"))
        connection.execute(text("DELETE FROM pipeline_runs"))
        connection.execute(text("DELETE FROM editorial_reviews"))
        connection.execute(text("DELETE FROM plant_profile_revisions"))
        connection.execute(text("DELETE FROM plant_profile_sources"))
        connection.execute(text("DELETE FROM plant_profiles"))
        connection.execute(text("DELETE FROM source_records"))
        connection.execute(
            text(
                """
                DELETE FROM sources
                WHERE identifier in (
                    'kew-powo', 'ema-herbal', 'nccih', 'wikimedia-commons',
                    'fixture-discovery'
                )
                """
            )
        )


def login_client(client) -> None:
    response = client.post("/api/v1/auth/login", json=TEST_LOGIN)
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert "httponly" in response.headers["set-cookie"].lower()


def test_auth_login_session_and_logout(client) -> None:
    wrong_email = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.invalid", "password": "test-password"},
    )
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "test-admin@example.invalid", "password": "wrong-password"},
    )

    assert wrong_email.status_code == 401
    assert wrong_password.status_code == 401
    assert wrong_email.json()["detail"] == wrong_password.json()["detail"]
    assert "test-password" not in wrong_email.text

    login_client(client)
    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json() == {
        "authenticated": True,
        "user": {
            "initials": "HB",
            "label": "Local admin",
            "role": "Milestone 2 editor",
        },
    }

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["authenticated"] is False
    assert client.get("/api/v1/auth/session").json()["authenticated"] is False


def test_newsletter_subscription_validates_normalizes_and_deduplicates(client) -> None:
    invalid = client.post("/api/v1/newsletter/subscriptions", json={"email": "bad"})
    first = client.post(
        "/api/v1/newsletter/subscriptions", json={"email": "  Reader@Example.COM "}
    )
    duplicate = client.post(
        "/api/v1/newsletter/subscriptions", json={"email": "reader@example.com"}
    )

    assert invalid.status_code == 422
    assert first.status_code == 200
    assert first.json()["email"] == "reader@example.com"
    assert first.json()["status"] == "subscribed"
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "already_subscribed"

    with get_session_factory()() as session:
        count = session.scalar(select(func.count()).select_from(NewsletterSubscription))
    assert count == 1


def test_public_endpoints_hide_review_profiles_until_published(client) -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)

    response = client.get("/api/v1/plants")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert all(item["status"] == "published" for item in payload["items"])
    assert not any(item["slug"] == "german-chamomile" for item in payload["items"])

    detail = client.get("/api/v1/plants/german-chamomile")
    assert detail.status_code == 404


def test_editorial_approval_then_publication_makes_profile_public(client) -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)

    login_client(client)
    reviews = client.get("/api/v1/admin/reviews")
    assert reviews.status_code == 200
    review = next(
        item
        for item in reviews.json()
        if item["plant_profile"] and item["plant_profile"]["slug"] == "german-chamomile"
    )

    publish_before_approval = client.post(
        f"/api/v1/admin/plants/{review['plant_profile']['id']}/publish"
    )
    assert publish_before_approval.status_code == 409

    approved = client.post(
        f"/api/v1/admin/reviews/{review['id']}/approve",
        json={"reviewer_name": "Milestone 2 test editor"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    published = client.post(
        f"/api/v1/admin/plants/{review['plant_profile']['id']}/publish"
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["sources"]

    public_detail = client.get("/api/v1/plants/german-chamomile")
    assert public_detail.status_code == 200
    assert public_detail.json()["display_common_name"] == "German chamomile"
    assert public_detail.json()["source_count"] == sum(
        source["source_type"] != "licensed_media"
        for source in public_detail.json()["sources"]
    )


def test_editorial_api_requires_authenticated_session(client) -> None:
    response = client.get("/api/v1/admin/reviews")

    assert response.status_code == 401
    assert "local development access header" not in response.text
    assert "test-password" not in response.text


def test_agent_performance_aggregates_real_pipeline_stages(client) -> None:
    with get_session_factory()() as session:
        run_fixture_pipeline(session)

    login_client(client)
    response = client.get("/api/v1/admin/agent-performance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_runs"] == 1
    assert payload["auto_published"] == 0
    assert payload["stages"]
    assert any(stage["name"] == "collect" for stage in payload["stages"])


def test_seed_is_idempotent() -> None:
    with get_session_factory()() as session:
        first = seed_curated_profiles(session)
        second = seed_curated_profiles(session)

    assert second["profiles_total"] == first["profiles_total"]
    assert second["source_records_total"] == first["source_records_total"]
    assert second["profiles_created"] == 0
    assert second["source_links_created"] == 0
    assert first["profiles_total"] == 30
    assert first["source_records_total"] == 92


def test_public_plant_paging_search_and_filters(client) -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        profiles = list(
            session.scalars(
                select(PlantProfile).order_by(PlantProfile.display_common_name)
            ).all()
        )
        for profile in profiles[:13]:
            profile.status = "published"
            profile.approved_at = datetime.now(timezone.utc)
            profile.published_at = datetime.now(timezone.utc)
        session.commit()

    first_page = client.get("/api/v1/plants?page=1&page_size=12")
    second_page = client.get("/api/v1/plants?page=2&page_size=12")
    search = client.get("/api/v1/plants?query=ginseng")
    family = client.get("/api/v1/plants?family=Asteraceae")
    tag = client.get("/api/v1/plants?tag=India")

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 13
    assert len(first_page.json()["items"]) == 12
    assert len(second_page.json()["items"]) == 1
    assert all(
        "ginseng" in item["display_common_name"].lower()
        for item in search.json()["items"]
    )
    assert all(item["family_name"] == "Asteraceae" for item in family.json()["items"])
    assert all("India" in item["diversity_tags"] for item in tag.json()["items"])


def test_import_preserves_human_reviewed_profile_text() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        profile = session.scalar(
            select(PlantProfile).where(PlantProfile.slug == "peppermint")
        )
        assert profile is not None
        profile.status = "published"
        profile.approved_at = datetime.now(timezone.utc)
        profile.published_at = datetime.now(timezone.utc)
        profile.summary = "Human-reviewed summary that must survive re-import."
        session.commit()

        result = seed_curated_profiles(session)
        session.refresh(profile)

        assert result["profiles_protected"] == 1
        assert profile.summary == "Human-reviewed summary that must survive re-import."
        assert profile.hero_image["kind"] == "licensed_photograph"


def _make_peppermint_version_one() -> None:
    with get_session_factory()() as session:
        profile = session.scalar(
            select(PlantProfile).where(PlantProfile.slug == "peppermint")
        )
        assert profile is not None
        profile.version = 1
        profile.status = "published"
        profile.summary = "Published version one summary."
        profile.introduction = "Published version one introduction."
        profile.approved_at = datetime.now(timezone.utc)
        profile.published_at = datetime.now(timezone.utc)
        session.commit()


def test_pending_revision_workflow_preserves_public_content_until_promotion(
    client,
) -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
    _make_peppermint_version_one()

    with get_session_factory()() as session:
        first_import = seed_curated_profiles(session)
        second_import = seed_curated_profiles(session)
        revisions = list(
            session.scalars(
                select(PlantProfileRevision).where(
                    PlantProfileRevision.plant_profile.has(slug="peppermint")
                )
            ).all()
        )

    assert first_import["revisions_created"] == 1
    assert second_import["revisions_created"] == 0
    assert second_import["revisions_unchanged"] >= 1
    assert len(revisions) == 1
    assert revisions[0].version == 3
    assert revisions[0].status == "needs_review"

    before = client.get("/api/v1/plants/peppermint")
    assert before.status_code == 200
    assert before.json()["version"] == 1
    assert before.json()["introduction"] == "Published version one introduction."

    login_client(client)
    revision_queue = client.get("/api/v1/admin/revisions")
    assert revision_queue.status_code == 200
    peppermint = next(
        item for item in revision_queue.json() if item["slug"] == "peppermint"
    )
    assert peppermint["current_version"] == 1
    assert peppermint["proposed_version"] == 3
    assert peppermint["current_content"]["introduction"] == (
        "Published version one introduction."
    )
    assert len(peppermint["proposed_content"]["introduction"].split()) >= 50

    gated = client.post(f"/api/v1/admin/revisions/{peppermint['id']}/promote")
    assert gated.status_code == 409

    approved = client.post(
        f"/api/v1/admin/revisions/{peppermint['id']}/approve",
        json={"reviewer_name": "Milestone 2B test editor"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    still_public_v1 = client.get("/api/v1/plants/peppermint")
    assert still_public_v1.json()["version"] == 1

    promoted = client.post(f"/api/v1/admin/revisions/{peppermint['id']}/promote")
    assert promoted.status_code == 200
    assert promoted.json()["status"] == "promoted"
    assert promoted.json()["current_version"] == 3

    after = client.get("/api/v1/plants/peppermint")
    assert after.status_code == 200
    assert after.json()["version"] == 3
    assert (
        after.json()["introduction"] == peppermint["proposed_content"]["introduction"]
    )
    assert after.json()["source_count"] == sum(
        source["source_type"] != "licensed_media" for source in after.json()["sources"]
    )
    assert after.json()["hero_image"]["attribution"]

    with get_session_factory()() as session:
        history = list(
            session.scalars(
                select(PlantProfileRevision)
                .join(PlantProfile)
                .where(PlantProfile.slug == "peppermint")
                .order_by(PlantProfileRevision.version)
            ).all()
        )
    assert [(item.version, item.status) for item in history] == [
        (1, "superseded"),
        (3, "promoted"),
    ]


def test_revision_hold_requires_reason_and_never_changes_public_profile(client) -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
    _make_peppermint_version_one()
    with get_session_factory()() as session:
        seed_curated_profiles(session)

    login_client(client)
    revision = next(
        item
        for item in client.get("/api/v1/admin/revisions").json()
        if item["slug"] == "peppermint"
    )
    missing_reason = client.post(
        f"/api/v1/admin/revisions/{revision['id']}/reject",
        json={"reviewer_name": "Test editor", "reason": ""},
    )
    assert missing_reason.status_code == 422

    held = client.post(
        f"/api/v1/admin/revisions/{revision['id']}/reject",
        json={"reviewer_name": "Test editor", "reason": "Needs source review."},
    )
    assert held.status_code == 200
    assert held.json()["status"] == "held"
    assert held.json()["decision_reason"] == "Needs source review."
    approved = client.post(
        f"/api/v1/admin/revisions/{revision['id']}/approve",
        json={"reviewer_name": "Test editor"},
    )
    assert approved.status_code == 200
    held_again = client.post(
        f"/api/v1/admin/revisions/{revision['id']}/reject",
        json={"reviewer_name": "Test editor", "reason": "Approval revoked."},
    )
    assert held_again.status_code == 200
    assert held_again.json()["status"] == "held"
    assert held_again.json()["decision_reason"] == "Approval revoked."
    public = client.get("/api/v1/plants/peppermint")
    assert public.json()["version"] == 1


def test_changed_protected_content_requires_a_new_manifest_version() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        profile = session.scalar(
            select(PlantProfile).where(PlantProfile.slug == "peppermint")
        )
        assert profile is not None
        profile.status = "published"
        profile.summary = "Human-edited content at the same version."
        session.commit()

        with pytest.raises(
            ValueError, match="content changed without increasing content_version"
        ):
            seed_curated_profiles(session)


def test_older_manifest_version_is_skipped_without_canonical_overwrite() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        profile = session.scalar(
            select(PlantProfile).where(PlantProfile.slug == "peppermint")
        )
        assert profile is not None
        profile.version = 4
        profile.summary = "Newer human-authored canonical content."
        session.commit()
        result = seed_curated_profiles(session)
        session.refresh(profile)

    assert result["older_versions_skipped"] == 1
    assert profile.version == 4
    assert profile.summary == "Newer human-authored canonical content."


def test_revision_constraints_prevent_duplicate_version_and_checksum() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        profile = session.scalar(
            select(PlantProfile).where(PlantProfile.slug == "peppermint")
        )
        assert profile is not None
        first = PlantProfileRevision(
            plant_profile_id=profile.id,
            version=4,
            content_payload={"profile": {}, "source_refs": []},
            content_checksum="a" * 64,
            status="needs_review",
        )
        session.add(first)
        session.commit()
        session.add(
            PlantProfileRevision(
                plant_profile_id=profile.id,
                version=4,
                content_payload={"profile": {"changed": True}, "source_refs": []},
                content_checksum="b" * 64,
                status="needs_review",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(
            PlantProfileRevision(
                plant_profile_id=profile.id,
                version=5,
                content_payload={"profile": {"changed": True}, "source_refs": []},
                content_checksum="a" * 64,
                status="needs_review",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_source_records_reject_duplicate_canonical_url() -> None:
    engine = get_engine()
    identifier = f"duplicate-test-{uuid.uuid4()}"
    canonical_url = f"https://example.org/duplicate/{uuid.uuid4()}"
    created_at = datetime.now(timezone.utc)

    with engine.begin() as connection:
        source_id = uuid.uuid4()
        connection.execute(
            text(
                """
                INSERT INTO sources (
                    id, identifier, name, base_url, status, created_at, updated_at
                ) VALUES (
                    :id, :identifier, 'Duplicate Test Source',
                    'https://example.org', 'approved', :created_at, :created_at
                )
                """
            ),
            {"id": source_id, "identifier": identifier, "created_at": created_at},
        )
        for suffix in ("a", "b"):
            params = {
                "id": uuid.uuid4(),
                "source_id": source_id,
                "external_identifier": f"{identifier}-{suffix}",
                "canonical_url": canonical_url,
                "created_at": created_at,
            }
            if suffix == "b":
                with pytest.raises(IntegrityError):
                    connection.execute(_source_record_insert_sql(), params)
            else:
                connection.execute(_source_record_insert_sql(), params)

    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM sources WHERE identifier = :identifier"),
            {"identifier": identifier},
        )


def _source_record_insert_sql():
    return text(
        """
        INSERT INTO source_records (
            id, source_id, external_identifier, url, canonical_url, title, publisher,
            source_type, original_language, license_status, supports, permitted_extract,
            parser_version, content_hash, source_publication_date, collected_at,
            created_at, updated_at
        ) VALUES (
            :id, :source_id, :external_identifier, 'https://example.org/raw',
            :canonical_url, 'Duplicate Source Record', 'Fixture Source',
            'fixture', 'en', 'fixture use only', '{}', 'fixture text',
            'test-v1', 'duplicate-content-hash', NULL, :created_at,
            :created_at, :created_at
        )
        """
    )


def test_fixture_pipeline_is_idempotent_and_held_for_review() -> None:
    with get_session_factory()() as session:
        first = run_fixture_pipeline(session)
        first_id = first.id
        second = run_fixture_pipeline(session)
        source_records = session.scalars(
            select(SourceRecord).where(
                SourceRecord.canonical_url
                == "https://example.org/fixtures/chamomile-quality-note"
            )
        ).all()
        public_fixture_profiles = session.scalars(
            select(PlantProfile).where(PlantProfile.slug.like("fixture%"))
        ).all()
        editorial_reviews = session.scalars(select(EditorialReview)).all()
        review_stage = next(
            stage
            for stage in second.stages
            if stage.name == "create_editorial_review_item"
        )

    assert second.id == first_id
    assert second.status == "held"
    assert second.summary["auto_published"] == 0
    assert second.summary["held_source_records"] == 1
    assert second.summary["review_items_created"] == 0
    assert review_stage.status == "skipped"
    assert len(source_records) == 1
    assert editorial_reviews == []
    assert public_fixture_profiles == []


def test_editorial_reviews_reject_null_plant_profile_id() -> None:
    engine = get_engine()
    created_at = datetime.now(timezone.utc)

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO editorial_reviews (
                        id,
                        plant_profile_id,
                        content_type,
                        status,
                        reviewer_name,
                        decision_reason,
                        review_payload,
                        created_at,
                        decided_at
                    ) VALUES (
                        :id,
                        NULL,
                        'plant_profile',
                        'needs_review',
                        NULL,
                        NULL,
                        '{}'::jsonb,
                        :created_at,
                        NULL
                    )
                    """
                ),
                {"id": uuid.uuid4(), "created_at": created_at},
            )


def test_plant_profiles_cannot_be_deleted_while_editorial_reviews_exist() -> None:
    engine = get_engine()

    with get_session_factory()() as session:
        seed_curated_profiles(session)
        profile_id = session.scalar(
            select(PlantProfile.id).where(PlantProfile.slug == "german-chamomile")
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM plant_profiles WHERE id = :profile_id"),
                {"profile_id": profile_id},
            )

    with get_session_factory()() as session:
        review_count = len(
            session.scalars(
                select(EditorialReview).where(
                    EditorialReview.plant_profile_id == profile_id
                )
            ).all()
        )

    assert review_count == 1
