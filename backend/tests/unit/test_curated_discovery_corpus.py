import json

import pytest
from backend.app.domains.discovery.corpus import (
    CuratedDiscoveryCorpus,
    load_curated_discovery_corpus,
)
from pydantic import ValidationError


def test_curated_corpus_has_ten_unique_real_traceable_records() -> None:
    corpus = load_curated_discovery_corpus()
    assert len(corpus.articles) == 10
    assert len({article.slug for article in corpus.articles}) == 10
    assert len({article.plant_slug for article in corpus.articles}) == 10
    assert len({article.sources[0].pmid for article in corpus.articles}) == 10
    assert len({article.sources[0].doi for article in corpus.articles}) == 10
    assert all(
        article.sources[0].retraction_status == "checked_clear"
        for article in corpus.articles
    )
    assert all(
        article.content_checksum == article.calculated_checksum()
        for article in corpus.articles
    )
    assert all(len(article.section_sources) == 11 for article in corpus.articles)
    assert all(
        article.image_caption.startswith("Botanical reference image")
        for article in corpus.articles
    )


def test_geography_must_reference_a_declared_source() -> None:
    payload = load_curated_discovery_corpus().model_dump(mode="json")
    payload["articles"][0]["geography"] = [
        {
            "country_or_region": "Nowhere",
            "iso_country_code": "ZZ",
            "evidence_type": "study_site",
            "source_id": "pubmed:missing",
            "supporting_text_location": "Abstract",
            "confidence": "qualified",
            "qualification": "Invalid test record",
            "display_label": "Nowhere",
            "map_title": "Where the clinical study was conducted",
        }
    ]
    payload["articles"][0]["content_checksum"] = "0" * 64
    with pytest.raises(ValidationError, match="geography source"):
        CuratedDiscoveryCorpus.model_validate(payload)


def test_same_version_source_mutation_breaks_content_checksum() -> None:
    payload = json.loads(
        json.dumps(load_curated_discovery_corpus().model_dump(mode="json"))
    )
    payload["articles"][0]["headline"] += " changed"
    with pytest.raises(ValidationError, match="content checksum mismatch"):
        CuratedDiscoveryCorpus.model_validate(payload)
