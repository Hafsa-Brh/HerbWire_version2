import hashlib
from pathlib import Path

import pytest
from backend.app.domains.encyclopedia.corpus import DistributionRegion, load_corpus

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_corpus_has_three_complete_batches_and_unique_taxa() -> None:
    manifest = load_corpus()

    assert len(manifest.profiles) == 30
    assert {
        batch: sum(p.batch == batch for p in manifest.profiles) for batch in "ABC"
    } == {
        "A": 10,
        "B": 10,
        "C": 10,
    }
    assert len({profile.slug for profile in manifest.profiles}) == 30
    assert (
        len({profile.accepted_scientific_name for profile in manifest.profiles}) == 30
    )
    assert all(profile.taxon_status == "accepted" for profile in manifest.profiles)
    assert all(
        profile.readiness_status == "ready_for_review" for profile in manifest.profiles
    )


def test_every_profile_has_section_sources_safety_and_distribution() -> None:
    manifest = load_corpus()

    for profile in manifest.profiles:
        support = {
            item for reference in profile.source_refs for item in reference.supports
        }
        assert {"taxonomy", "distribution", "traditional_use", "safety"} <= support
        assert profile.traditional_uses
        assert profile.parts_used
        assert profile.safety_notes
        assert len(profile.introduction.split()) >= 50
        assert len(profile.evidence_notes.split()) >= 30
        assert len(profile.preparation.split()) >= 25
        assert len(profile.safety_notes) >= 2
        assert {region.status for region in profile.distribution} >= {"introduced"}
        assert {region.status for region in profile.distribution} & {
            "native",
            "unknown",
        }


def test_every_media_asset_exists_and_matches_licensed_metadata() -> None:
    manifest = load_corpus()
    checksums: set[str] = set()

    for profile in manifest.profiles:
        media = profile.media
        path = (
            REPOSITORY_ROOT / "frontend" / "public" / media.local_path.removeprefix("/")
        )
        assert path.is_file(), profile.slug
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        assert checksum == media.checksum_sha256
        assert checksum not in checksums
        checksums.add(checksum)
        assert media.attribution
        assert media.creator
        assert "creator listed on" not in media.creator.casefold()
        assert media.license
        assert media.license_url
        assert media.kind == "licensed_photograph"
        assert "illustration" not in media.file_title.casefold()
        assert "herbarium" not in media.file_title.casefold()
        assert not media.file_title.startswith("File:COI")
        assert media.width >= 1200
        assert media.height >= 800


def test_distribution_map_country_codes_are_valid_and_source_scoped() -> None:
    manifest = load_corpus()
    mapped = {
        profile.slug: [
            country
            for region in profile.distribution
            for country in region.map_countries
        ]
        for profile in manifest.profiles
        if any(region.map_countries for region in profile.distribution)
    }

    assert set(mapped) == {profile.slug for profile in manifest.profiles}
    assert all(countries for countries in mapped.values())
    assert all(
        any(
            reference.source_id == "gbif-wcvp-dataset"
            and "distribution" in reference.supports
            for reference in profile.source_refs
        )
        for profile in manifest.profiles
    )
    assert all(
        len(region.map_countries) == len(set(region.map_countries))
        for profile in manifest.profiles
        for region in profile.distribution
    )
    assert all(
        len(country) == 2 and country.isupper()
        for countries in mapped.values()
        for country in countries
    )

    with pytest.raises(ValueError, match="ISO 3166-1"):
        DistributionRegion(
            code="bad",
            name="Bad",
            status="native",
            level=0,
            map_countries=["USA"],
        )


def test_corpus_avoids_unsupported_marketing_language() -> None:
    content = (
        Path(
            REPOSITORY_ROOT
            / "backend"
            / "app"
            / "domains"
            / "encyclopedia"
            / "corpus.json"
        )
        .read_text(encoding="utf-8")
        .casefold()
    )

    assert "guaranteed treatment" not in content
    assert "clinically proven" not in content
    assert "miracle cure" not in content
    assert "\u00e3" not in content
    assert "\ufffd" not in content


def test_rich_article_pilot_is_versioned_preparation_specific_and_traceable() -> None:
    manifest = load_corpus()
    pilots = {
        profile.slug: profile
        for profile in manifest.profiles
        if profile.slug in {"lavender", "senna", "peppermint"}
    }

    assert set(pilots) == {"lavender", "senna", "peppermint"}
    assert all(profile.content_version == 4 for profile in pilots.values())
    assert all(profile.article_details.preparation_forms for profile in pilots.values())
    assert all(profile.article_details.evidence_findings for profile in pilots.values())
    assert all(
        profile.article_details.special_populations for profile in pilots.values()
    )
    assert all(profile.article_details.section_sources for profile in pilots.values())
    assert {
        form.route for form in pilots["lavender"].article_details.preparation_forms
    } == {"oral", "inhaled", "topical"}
    assert pilots["senna"].parts_used == ["leaflets"]
    assert {
        form.route for form in pilots["senna"].article_details.preparation_forms
    } == {"oral"}
    assert len(pilots["peppermint"].article_details.preparation_forms) == 4
    assert any(
        "leaf" in form.label.casefold()
        for form in pilots["peppermint"].article_details.preparation_forms
    )
    assert any(
        "oil" in form.label.casefold()
        for form in pilots["peppermint"].article_details.preparation_forms
    )


def test_rich_article_medical_claims_have_linked_source_ids() -> None:
    manifest = load_corpus()
    for profile in (
        item
        for item in manifest.profiles
        if item.slug in {"lavender", "senna", "peppermint"}
    ):
        linked = {reference.source_id for reference in profile.source_refs}
        items = [
            *profile.article_details.preparation_forms,
            *profile.article_details.evidence_findings,
            *profile.article_details.mechanisms,
            *profile.article_details.special_populations,
            *profile.article_details.interactions,
        ]
        assert items
        assert all(item.source_ids and set(item.source_ids) <= linked for item in items)
        assert all(
            note.source_ids and set(note.source_ids) <= linked
            for note in profile.safety_notes
        )


def test_recovery_batch_one_is_rich_versioned_and_source_traceable() -> None:
    manifest = load_corpus()
    expected = {
        "german-chamomile",
        "ginger",
        "turmeric",
        "garlic",
        "fennel",
        "asian-ginseng",
        "black-cohosh",
        "boswellia",
        "devils-claw",
    }
    profiles = {
        profile.slug: profile
        for profile in manifest.profiles
        if profile.slug in expected
    }

    assert set(profiles) == expected
    for profile in profiles.values():
        details = profile.article_details
        linked = {reference.source_id for reference in profile.source_refs}
        media_ids = {
            reference.source_id
            for reference in profile.source_refs
            if reference.support_role == "licensed_media"
        }
        assert profile.content_version == 4
        assert details.preparation_forms
        assert details.evidence_findings
        assert details.special_populations
        required_sections = {
            "overview",
            "botanical",
            "preparations",
            "evidence",
            "safety",
            "distribution",
        }
        assert required_sections <= set(details.section_sources)
        assert all(
            set(source_ids) <= linked for source_ids in details.section_sources.values()
        )
        assert all(
            not (set(source_ids) & media_ids)
            for source_ids in details.section_sources.values()
        )
        assert all(item.equivalence_warning for item in details.preparation_forms)
        assert all(item.limitations for item in details.evidence_findings)
