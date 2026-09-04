import json
from pathlib import Path

import pytest
from backend.app.domains.materials.corpus import (
    CuratedMaterialCorpus,
    load_curated_material_corpus,
)
from pydantic import ValidationError


def test_material_corpus_has_exactly_seven_traceable_licensed_stories() -> None:
    corpus = load_curated_material_corpus()

    assert len(corpus.stories) == 7
    assert len({story.id for story in corpus.stories}) == 7
    assert len({story.slug for story in corpus.stories}) == 7
    assert sum(story.featured for story in corpus.stories) == 1
    assert all(len(story.sections) >= 6 for story in corpus.stories)
    assert all(len(story.sources) >= 2 for story in corpus.stories)

    root = Path(__file__).resolve().parents[3] / "frontend" / "public"
    for story in corpus.stories:
        assert story.content_checksum
        assert (root / story.hero_media.local_path.removeprefix("/")).is_file()
        declared = {source.source_id for source in story.sources}
        assert all(set(section.source_ids) <= declared for section in story.sections)
        assert story.hero_media.license
        assert str(story.hero_media.license_url).startswith("https://")


def test_material_corpus_rejects_untraceable_sections() -> None:
    payload = json.loads(load_curated_material_corpus().model_dump_json())
    payload["stories"][0]["sections"][0]["source_ids"] = ["missing:source"]

    with pytest.raises(ValidationError, match="every section source must resolve"):
        CuratedMaterialCorpus.model_validate(payload)


def test_material_corpus_rejects_missing_or_duplicate_story() -> None:
    payload = json.loads(load_curated_material_corpus().model_dump_json())
    payload["stories"].append(payload["stories"][0])

    with pytest.raises(ValidationError):
        CuratedMaterialCorpus.model_validate(payload)
