from copy import deepcopy

import pytest
from backend.app.db.session import get_engine, get_session_factory
from backend.app.domains.discovery.corpus import (
    load_curated_discovery_corpus,
    load_new_plant_discovery_corpus,
)
from backend.app.domains.discovery.curated_import import import_curated_discoveries
from backend.app.domains.discovery.service import (
    decide_discovery_article,
    publish_discovery_article,
)
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.models.encyclopedia import (
    DiscoveryArticle,
    EditorialReview,
    PlantProfile,
)
from sqlalchemy import func, select, text


@pytest.fixture(autouse=True)
def clean_database():
    statement = text("""TRUNCATE discovery_article_plants, discovery_article_sources,
        editorial_reviews, discovery_articles, discovery_events, plant_profile_sources,
        plant_profile_revisions, plant_profiles, source_records, pipeline_stage_results,
        pipeline_runs, newsletter_subscriptions RESTART IDENTITY CASCADE""")
    with get_engine().begin() as connection:
        connection.execute(statement)
    yield
    with get_engine().begin() as connection:
        connection.execute(statement)


def _prepare() -> None:
    with get_session_factory()() as session:
        seed_curated_profiles(session)
        for profile in session.scalars(select(PlantProfile)).all():
            profile.status = "published"
        session.commit()


def test_new_batch_is_idempotent_and_preserves_original_ten() -> None:
    _prepare()
    original = load_curated_discovery_corpus()
    new = load_new_plant_discovery_corpus()
    with get_session_factory()() as session:
        original_summary = import_curated_discoveries(session, original)
        before = {
            article.slug: article.content_checksum
            for article in session.scalars(select(DiscoveryArticle)).all()
        }
        first = import_curated_discoveries(session, new)
        second = import_curated_discoveries(session, new)
        articles = list(session.scalars(select(DiscoveryArticle)).all())
        reviews = session.scalar(
            select(func.count())
            .select_from(EditorialReview)
            .where(EditorialReview.discovery_article_id.is_not(None))
        )
    assert original_summary.created == 10
    assert first.created == first.reviews_created == 12
    assert first.source_records_created == 25
    assert (
        second.created == second.reviews_created == second.source_records_created == 0
    )
    assert second.unchanged == 12
    assert len(articles) == reviews == 22
    assert all(article.status == "needs_review" for article in articles)
    assert all(article.published_at is None for article in articles)
    assert all(
        article.content_checksum == before[article.slug]
        for article in articles
        if article.slug in before
    )


def test_standalone_article_requires_approval_then_can_publish() -> None:
    _prepare()
    with get_session_factory()() as session:
        import_curated_discoveries(session, load_new_plant_discovery_corpus())
        article = session.scalar(
            select(DiscoveryArticle).order_by(DiscoveryArticle.slug)
        )
        assert article is not None
        assert article.plant_links == []
        decide_discovery_article(session, article.id, "approved", "Editor", None)
        published = publish_discovery_article(session, article.id, "Editor")
        assert published.status == "published"
        assert (
            published.event.evidence_package["botanical_identity"]["accepted"] is True
        )


def test_changed_same_version_rolls_back_without_overwriting() -> None:
    _prepare()
    corpus = load_new_plant_discovery_corpus()
    with get_session_factory()() as session:
        import_curated_discoveries(session, corpus)
        changed = deepcopy(corpus)
        changed.articles[0].headline += " changed"
        changed.articles[0].content_checksum = changed.articles[0].calculated_checksum()
        with pytest.raises(ValueError, match="changed same-version"):
            import_curated_discoveries(session, changed)
        assert session.scalar(select(func.count()).select_from(DiscoveryArticle)) == 12
