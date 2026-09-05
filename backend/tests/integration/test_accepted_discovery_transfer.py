from copy import deepcopy

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.discovery import accepted_transfer
from backend.app.domains.discovery.accepted_transfer import (
    AcceptedDiscoveryManifest,
    _checksum,
    load_accepted_manifest,
    load_all_curated_discovery_corpora,
    transfer_owner_accepted_discoveries,
)
from backend.app.domains.discovery.curated_import import import_curated_discoveries
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    EditorialReview,
    PlantProfile,
)
from sqlalchemy import func, select, text


@pytest.fixture(autouse=True)
def clean_database():
    statement = text("""TRUNCATE material_story_sources, material_stories,
        discovery_article_plants, discovery_article_sources, editorial_reviews,
        discovery_articles, discovery_events, plant_profile_sources,
        plant_profile_revisions, plant_profiles, source_records,
        pipeline_stage_results, pipeline_runs, newsletter_subscriptions
        RESTART IDENTITY CASCADE""")
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


def _prepare_plants() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        for profile in session.scalars(select(PlantProfile)).all():
            profile.status = "published"
        session.commit()


def _fingerprints(session) -> dict[str, str | None]:
    statements = {
        "plants": """select md5(string_agg(md5(row_to_json(p)::text), ''
            order by p.slug)) from plant_profiles p""",
        "plant_revisions": """select md5(string_agg(md5(row_to_json(r)::text), ''
            order by r.plant_profile_id::text,r.version))
            from plant_profile_revisions r""",
        "plant_reviews": """select md5(string_agg(md5(row_to_json(r)::text), ''
            order by r.id::text)) from editorial_reviews r
            where r.plant_profile_id is not null""",
        "plant_links": """select md5(string_agg(md5(row_to_json(l)::text), ''
            order by l.plant_profile_id::text,l.source_record_id::text,
            l.support_role)) from plant_profile_sources l""",
    }
    return {
        key: session.scalar(text(statement)) for key, statement in statements.items()
    }


def _resign_manifest(manifest: AcceptedDiscoveryManifest):
    payload = manifest.model_dump(mode="json")
    payload["manifest_checksum"] = _checksum(
        {key: value for key, value in payload.items() if key != "manifest_checksum"}
    )
    return AcceptedDiscoveryManifest.model_validate(payload)


def test_dry_run_is_read_only_and_live_transfer_is_idempotent() -> None:
    _prepare_plants()
    with get_session_factory()() as session:
        before = _fingerprints(session)
        dry = transfer_owner_accepted_discoveries(session, dry_run=True)
        assert dry.created == dry.transferred == dry.verified == 30
        assert session.scalar(select(func.count()).select_from(DiscoveryArticle)) == 0

        first = transfer_owner_accepted_discoveries(session)
        after_first = _fingerprints(session)
        second = transfer_owner_accepted_discoveries(session)
        articles = list(session.scalars(select(DiscoveryArticle)).all())
        reviews = list(
            session.scalars(
                select(EditorialReview).where(
                    EditorialReview.discovery_article_id.is_not(None)
                )
            ).all()
        )
        rich_content_valid = all(
            article.sources
            and article.section_sources
            and (article.plant_links or article.geography)
            for article in articles
        )
        primary_records = [
            link.source_record
            for article in articles
            for link in article.sources
            if link.support_role == "primary_evidence"
        ]
        primary_pmids = {record.external_identifier for record in primary_records}
        primary_dois = {record.doi for record in primary_records}
        mapped_articles = sum(bool(article.geography) for article in articles)

    assert first.created == first.transferred == 30
    assert first.unchanged == 0
    assert second.created == second.transferred == 0
    assert second.unchanged == second.verified == 30
    assert before == after_first
    assert len(articles) == len(reviews) == 30
    assert {article.status for article in articles} == {"published"}
    assert all(article.published_at and article.hero_image for article in articles)
    assert rich_content_valid
    assert len(primary_records) == len(primary_pmids) == len(primary_dois) == 30
    assert None not in primary_dois
    assert mapped_articles == 23
    assert {review.status for review in reviews} == {"approved"}
    assert not any(article.content_origin == "synthetic" for article in articles)


def test_content_identity_mismatch_is_rejected_without_writes() -> None:
    _prepare_plants()
    corpora = deepcopy(load_all_curated_discovery_corpora())
    corpora[0].articles[0].headline += " mutated"
    corpora[0].articles[0].content_checksum = (
        corpora[0].articles[0].calculated_checksum()
    )

    with get_session_factory()() as session:
        with pytest.raises(ValueError, match="manifest corpus checksum differs"):
            transfer_owner_accepted_discoveries(session, corpora=corpora)
        assert session.scalar(select(func.count()).select_from(DiscoveryArticle)) == 0


def test_existing_conflicting_editorial_state_is_never_repaired() -> None:
    _prepare_plants()
    first_corpus = load_all_curated_discovery_corpora()[0]
    with get_session_factory()() as session:
        import_curated_discoveries(session, first_corpus)
        article = session.scalar(select(DiscoveryArticle))
        assert article is not None
        article.status = "held"
        article.reviews[0].status = "held"
        article.reviews[0].decision_reason = "Owner review remains unresolved."
        session.commit()
        with pytest.raises(ValueError, match="editorial state conflicts"):
            transfer_owner_accepted_discoveries(session)
        session.refresh(article)
        assert article.status == "held"


def test_forced_mid_operation_failure_rolls_back_every_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_plants()
    original = accepted_transfer.import_curated_discoveries
    calls = 0

    def fail_after_first(session, corpus, *, commit=True):
        nonlocal calls
        calls += 1
        summary = original(session, corpus, commit=commit)
        if calls == 2:
            raise RuntimeError("forced transfer failure")
        return summary

    monkeypatch.setattr(
        accepted_transfer, "import_curated_discoveries", fail_after_first
    )
    with get_session_factory()() as session:
        with pytest.raises(RuntimeError, match="forced transfer failure"):
            transfer_owner_accepted_discoveries(session)
        assert session.scalar(select(func.count()).select_from(DiscoveryArticle)) == 0


def test_manifest_primary_identity_mismatch_is_rejected() -> None:
    _prepare_plants()
    manifest = load_accepted_manifest()
    payload = manifest.model_dump(mode="json")
    payload["decisions"][0]["primary_doi"] = "10.0000/not-accepted"
    payload["manifest_checksum"] = _checksum(
        {key: value for key, value in payload.items() if key != "manifest_checksum"}
    )
    changed = AcceptedDiscoveryManifest.model_validate(payload)

    with get_session_factory()() as session:
        with pytest.raises(ValueError, match="accepted identity differs"):
            transfer_owner_accepted_discoveries(session, manifest=changed)
