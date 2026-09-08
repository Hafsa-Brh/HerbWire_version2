import shutil

import pytest
from backend.app.domains.discovery.pipeline_catalog import (
    load_discovery_pipeline_catalog,
)
from backend.app.domains.encyclopedia.plant_eligibility import (
    candidate_identity_keys,
    normalize_identity,
)
from backend.app.domains.encyclopedia.plant_pipeline_catalog import (
    PROJECT_ROOT,
    load_plant_pipeline_catalog,
)


def test_catalogue_is_bounded_source_led_and_media_verified() -> None:
    catalog = load_plant_pipeline_catalog()

    assert [candidate.key for candidate in catalog.candidates] == [
        "yarrow",
        "hop",
        "horse-chestnut",
        "bearberry",
        "centaury",
        "gentian",
        "meadowsweet",
        "stinging-nettle",
        "raspberry",
        "artichoke",
        "bilberry",
        "elder",
        "european-goldenrod",
        "marshmallow",
        "ivy",
        "arnica",
        "eucalyptus",
        "cowslip",
        "heartsease",
        "witch-hazel",
        "butchers-broom",
        "java-tea",
        "chaste-tree",
        "guarana",
        "silver-birch",
    ]
    assert len(catalog.candidates) == 25
    for candidate in catalog.candidates:
        package = catalog.package_for(candidate.key)
        assert len(package.sources) == 3
        assert package.profile.readiness_status == "ready_for_review"
        assert package.profile.media.kind == "licensed_photograph"
        assert package.profile.media.local_path.startswith("/media/plants/pipeline-")


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("Achillea millefolium L.", "  ACHILLEA\u2014MILLEFOLIUM L "),
        ("Hippocastanum vulgare", "hippocastanum-vulgare"),
        ("Y\u00e1rrow", "YARROW"),
    ],
)
def test_identity_normalization_handles_unicode_case_space_and_punctuation(
    left: str, right: str
) -> None:
    assert normalize_identity(left) == normalize_identity(right)


def test_candidate_keys_cover_taxon_scientific_synonyms_and_common_names() -> None:
    candidate = load_plant_pipeline_catalog().candidates[0]
    keys = candidate_identity_keys(candidate)

    assert "taxon:urnlsidipniorgnames22942" in keys
    assert "scientific:achilleamillefoliuml" in keys
    assert "scientific:achillealanulosanutt" in keys
    assert "common:yarrow" in keys


def test_media_checksum_and_path_validation_fail_closed() -> None:
    catalog = load_plant_pipeline_catalog(validate_media=False)

    with pytest.raises(ValueError, match="media path is missing or unsafe"):
        catalog.validate_media_files(PROJECT_ROOT / "missing-pipeline-media-root")

    assert PROJECT_ROOT.name == "HerbWire_version2"


def test_pipeline_media_resolves_from_production_build_layout(tmp_path) -> None:
    plant_catalog = load_plant_pipeline_catalog(validate_media=False)
    discovery_catalog = load_discovery_pipeline_catalog(validate_media=False)
    source_root = PROJECT_ROOT / "frontend" / "public"
    built_root = tmp_path / "frontend" / "dist"
    paths = [
        package.profile.media.local_path for package in plant_catalog.source_packages
    ] + [
        candidate.article.hero_image.local_path
        for candidate in discovery_catalog.candidates
        if candidate.article.hero_image is not None
    ]
    for local_path in paths:
        relative = local_path.removeprefix("/")
        destination = built_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / relative, destination)

    plant_catalog.validate_media_files(tmp_path)
    discovery_catalog.validate_media_files(tmp_path)
