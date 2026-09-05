import hashlib
import shutil
from pathlib import Path

import pytest
from backend.app.domains.discovery.accepted_transfer import (
    load_all_curated_discovery_corpora,
)
from backend.app.domains.discovery.curated_import import _validated_media
from backend.app.domains.materials.corpus import load_curated_material_corpus
from backend.app.domains.materials.curated_import import (
    resolve_material_media_path,
    validate_curated_material_media,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PUBLIC_ROOT = REPOSITORY_ROOT / "frontend" / "public"


def _copy_runtime_media(runtime_dist: Path) -> None:
    corpus = load_curated_material_corpus()
    for story in corpus.stories:
        relative = Path(story.hero_media.local_path.removeprefix("/"))
        destination = runtime_dist / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE_PUBLIC_ROOT / relative, destination)


def test_all_material_media_resolve_and_match_from_source_checkout() -> None:
    corpus = load_curated_material_corpus()

    validate_curated_material_media(corpus)

    resolved = [
        resolve_material_media_path(story.hero_media.local_path)
        for story in corpus.stories
    ]
    assert len(resolved) == 7
    for story, path in zip(corpus.stories, resolved, strict=True):
        assert path.is_relative_to(SOURCE_PUBLIC_ROOT.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == (
            story.hero_media.checksum_sha256
        )


def test_all_material_media_resolve_from_built_runtime_layout(tmp_path: Path) -> None:
    runtime_public = tmp_path / "app" / "frontend" / "public"
    runtime_dist = tmp_path / "app" / "frontend" / "dist"
    _copy_runtime_media(runtime_dist)
    corpus = load_curated_material_corpus()
    roots = (runtime_public, runtime_dist)

    validate_curated_material_media(corpus, media_roots=roots)

    for story in corpus.stories:
        path = resolve_material_media_path(
            story.hero_media.local_path, media_roots=roots
        )
        assert path.is_relative_to(runtime_dist.resolve())


def test_missing_material_media_still_fails_closed(tmp_path: Path) -> None:
    corpus = load_curated_material_corpus()

    with pytest.raises(ValueError, match="Licensed media is missing"):
        validate_curated_material_media(corpus, media_roots=(tmp_path,))


def test_changed_material_media_still_fails_checksum(tmp_path: Path) -> None:
    runtime_dist = tmp_path / "app" / "frontend" / "dist"
    _copy_runtime_media(runtime_dist)
    corpus = load_curated_material_corpus()
    first = corpus.stories[0]
    changed = runtime_dist / first.hero_media.local_path.removeprefix("/")
    changed.write_bytes(changed.read_bytes() + b"changed")

    with pytest.raises(ValueError, match="Licensed media checksum differs"):
        validate_curated_material_media(corpus, media_roots=(runtime_dist,))


@pytest.mark.parametrize(
    "local_path",
    (
        "/media/materials/../discoveries/image.jpg",
        "/media/materials/nested/image.jpg",
        "media/materials/image.jpg",
        "/media/materials/image.png",
    ),
)
def test_material_media_path_traversal_and_noncanonical_paths_are_rejected(
    local_path: str, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="outside the approved local directory"):
        resolve_material_media_path(local_path, media_roots=(tmp_path,))


def test_material_resolution_does_not_depend_on_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    validate_curated_material_media(load_curated_material_corpus())


def test_discovery_media_validation_remains_metadata_based() -> None:
    article = next(
        article
        for corpus in load_all_curated_discovery_corpora()
        for article in corpus.articles
        if article.hero_image is not None
    )

    assert _validated_media(article, None) == article.hero_image.model_dump(mode="json")
