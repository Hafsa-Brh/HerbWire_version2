import hashlib
from copy import deepcopy
from pathlib import Path

import pytest
from backend.app.core.settings import Settings
from backend.app.domains.discovery.corpus import (
    CuratedDiscoveryCorpus,
    load_curated_discovery_corpus,
    load_final_discovery_corpus,
    load_new_plant_discovery_corpus,
)
from backend.app.domains.encyclopedia.corpus import load_corpus
from pydantic import ValidationError
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]


def test_new_plant_corpus_is_distinct_rich_and_traceable() -> None:
    corpus = load_new_plant_discovery_corpus()
    original = load_curated_discovery_corpus()
    profiles = load_corpus()
    profile_names = {
        profile.accepted_scientific_name.casefold() for profile in profiles.profiles
    }
    assert len(corpus.articles) == 12
    assert len({article.scientific_name for article in corpus.articles}) == 12
    assert (
        not {article.scientific_name.casefold() for article in corpus.articles}
        & profile_names
    )
    assert not {article.common_name.casefold() for article in corpus.articles} & {
        article.common_name.casefold() for article in original.articles
    }
    assert all(article.plant_slug is None for article in corpus.articles)
    assert all(len(article.additional_sections) >= 6 for article in corpus.articles)
    assert all(len(article.sources) >= 2 for article in corpus.articles)
    assert all(
        {source.support_role for source in article.sources}
        >= {"primary_evidence", "taxonomy_distribution"}
        for article in corpus.articles
    )
    psyllium = next(
        article for article in corpus.articles if article.common_name == "Psyllium"
    )
    assert any(source.support_role == "safety" for source in psyllium.sources)
    assert any(
        source_id.startswith("ema-herbal:")
        for source_id in psyllium.section_sources["safety"].source_ids
    )
    assert all(
        article.botanical_identity and article.botanical_identity.accepted
        for article in corpus.articles
    )
    assert all(
        any(
            item.geography_kind == "botanical_distribution"
            for item in article.geography
        )
        for article in corpus.articles
    )
    assert (
        sum(
            article.hero_image.classification == "botanical_reference"
            for article in corpus.articles
            if article.hero_image
        )
        < len(corpus.articles) / 2
    )
    assert all(
        article.content_checksum == article.calculated_checksum()
        for article in corpus.articles
    )


def test_new_plant_identifiers_media_and_text_are_unique() -> None:
    corpus = load_new_plant_discovery_corpus()
    primary = [article.sources[0] for article in corpus.articles]
    assert len({source.pmid for source in primary}) == 12
    assert len({source.doi for source in primary}) == 12
    assert len({str(source.canonical_url) for source in primary}) == 12
    media = [article.hero_image for article in corpus.articles]
    assert len({item.stable_media_identifier for item in media if item}) == 12
    assert len({item.checksum_sha256 for item in media if item}) == 12
    section_text = [
        section.text
        for article in corpus.articles
        for section in article.additional_sections
    ]
    assert len(section_text) == len(set(section_text))
    assert all(
        "dose recommendation" not in article.practical_interpretation.casefold()
        for article in corpus.articles
    )


def test_new_plant_media_files_match_pinned_checksums() -> None:
    corpus = load_new_plant_discovery_corpus()
    for article in corpus.articles:
        assert article.hero_image is not None
        relative_path = article.hero_image.local_path.removeprefix("/")
        media_path = ROOT / "frontend" / "public" / relative_path
        assert media_path.is_file()
        assert (
            hashlib.sha256(media_path.read_bytes()).hexdigest()
            == article.hero_image.checksum_sha256
        )

    research_maps = [
        item
        for article in corpus.articles
        for item in article.geography
        if item.geography_kind == "research_geography"
    ]
    assert research_maps
    assert len(research_maps) < len(corpus.articles)
    assert all(item.source_id.startswith("pubmed:") for item in research_maps)


def test_new_plant_same_version_mutation_breaks_checksum() -> None:
    payload = deepcopy(load_new_plant_discovery_corpus().model_dump(mode="json"))
    payload["articles"][0]["standfirst"] += " Changed."
    with pytest.raises(ValidationError, match="content checksum mismatch"):
        CuratedDiscoveryCorpus.model_validate(payload)


def test_final_eight_are_unique_real_standalone_plants() -> None:
    final = load_final_discovery_corpus()
    existing = [
        *load_curated_discovery_corpus().articles,
        *load_new_plant_discovery_corpus().articles,
    ]
    profile_names = {
        profile.accepted_scientific_name.casefold()
        for profile in load_corpus().profiles
    }
    excluded_names = profile_names | {
        article.scientific_name.casefold() for article in existing
    }
    final_names = [article.scientific_name.casefold() for article in final.articles]
    assert len(final.articles) == len(set(final_names)) == 8
    assert not set(final_names) & excluded_names
    assert all(article.plant_slug is None for article in final.articles)
    assert all(article.botanical_identity for article in final.articles)
    assert all(len(article.additional_sections) >= 6 for article in final.articles)
    assert all(
        {source.support_role for source in article.sources}
        >= {"primary_evidence", "taxonomy_distribution"}
        for article in final.articles
    )
    rich_section_text = [
        section.text
        for article in final.articles
        for section in article.additional_sections
    ]
    assert len(rich_section_text) == len(set(rich_section_text))
    assert all(
        any(
            item.geography_kind == "botanical_distribution"
            for item in article.geography
        )
        for article in final.articles
    )
    assert all(
        article.content_checksum == article.calculated_checksum()
        for article in final.articles
    )


def test_final_eight_sources_and_media_are_pinned_and_unique() -> None:
    final = load_final_discovery_corpus()
    prior_articles = [
        *load_curated_discovery_corpus().articles,
        *load_new_plant_discovery_corpus().articles,
    ]
    existing_media = [
        article.hero_image
        for article in load_new_plant_discovery_corpus().articles
        if article.hero_image
    ]
    primary = [article.sources[0] for article in final.articles]
    assert len({source.pmid for source in primary}) == 8
    assert len({source.doi for source in primary}) == 8
    assert len({str(source.canonical_url) for source in primary}) == 8
    assert all(source.retraction_status == "checked_clear" for source in primary)
    assert not {
        source.source_id for article in final.articles for source in article.sources
    } & {source.source_id for article in prior_articles for source in article.sources}
    media = [article.hero_image for article in final.articles]
    assert len({item.stable_media_identifier for item in media if item}) == 8
    assert len({item.checksum_sha256 for item in media if item}) == 8
    assert not {item.stable_media_identifier for item in media if item} & {
        item.stable_media_identifier for item in existing_media
    }
    assert not {item.checksum_sha256 for item in media if item} & {
        item.checksum_sha256 for item in existing_media
    }
    prior_asset_hashes = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / "frontend" / "public" / "media").rglob("*")
        if path.is_file() and not path.name.startswith("m4c-final-")
    }
    assert not {item.checksum_sha256 for item in media if item} & prior_asset_hashes
    for article in final.articles:
        assert article.hero_image is not None
        media_path = (
            ROOT
            / "frontend"
            / "public"
            / article.hero_image.local_path.removeprefix("/")
        )
        assert media_path.is_file()
        assert (
            hashlib.sha256(media_path.read_bytes()).hexdigest()
            == article.hero_image.checksum_sha256
        )


def test_final_eight_same_version_mutation_breaks_checksum() -> None:
    payload = deepcopy(load_final_discovery_corpus().model_dump(mode="json"))
    payload["articles"][0]["standfirst"] += " Changed."
    with pytest.raises(ValidationError, match="content checksum mismatch"):
        CuratedDiscoveryCorpus.model_validate(payload)


def test_local_database_name_override_changes_only_database_name() -> None:
    base = "postgresql+psycopg://fixture-user:fixture-password@127.0.0.1:5433/original"
    settings = Settings(
        environment="local",
        database_url=base,
        local_database_name="herbwire_m4c_tests_20260903",
    )
    url = make_url(settings.database_url)
    assert url.database == "herbwire_m4c_tests_20260903"
    assert url.username == "fixture-user"
    assert url.host == "127.0.0.1"


def test_local_database_name_override_is_rejected_when_deployed() -> None:
    with pytest.raises(ValidationError, match="permitted only for local runtime"):
        Settings(
            environment="staging",
            database_url="postgresql+psycopg://fixture:fixture@db.invalid/test",
            local_database_name="another_database",
        )
