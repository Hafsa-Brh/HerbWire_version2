from copy import deepcopy

import pytest
from backend.app.domains.discovery.accepted_transfer import (
    EXPECTED_DISCOVERY_COUNT,
    AcceptedDiscoveryManifest,
    AcceptedTransferSummary,
    _checksum,
    load_accepted_manifest,
    load_all_curated_discovery_corpora,
    transfer_owner_accepted_discoveries,
)
from backend.app.workers import transfer_accepted_discoveries as worker


def _resigned(payload: dict) -> dict:
    payload["manifest_checksum"] = _checksum(
        {key: value for key, value in payload.items() if key != "manifest_checksum"}
    )
    return payload


def test_manifest_is_exactly_the_versioned_owner_accepted_set() -> None:
    manifest = load_accepted_manifest()

    assert len(manifest.decisions) == EXPECTED_DISCOVERY_COUNT
    assert manifest.manifest_checksum == manifest.calculated_checksum()
    assert len({item.slug for item in manifest.decisions}) == 30
    assert len({item.primary_pmid for item in manifest.decisions}) == 30
    assert len({item.primary_doi for item in manifest.decisions}) == 30
    assert {item.article_state for item in manifest.decisions} == {"published"}
    assert {item.review_state for item in manifest.decisions} == {"approved"}


def test_manifest_checksum_mutation_is_rejected() -> None:
    payload = load_accepted_manifest().model_dump(mode="json")
    payload["decisions"][0]["published_at"] = "2026-09-04T00:00:00Z"

    with pytest.raises(ValueError, match="manifest checksum mismatch"):
        AcceptedDiscoveryManifest.model_validate(payload)


def test_missing_manifest_record_is_rejected_even_when_resigned() -> None:
    payload = load_accepted_manifest().model_dump(mode="json")
    payload["decisions"].pop()

    with pytest.raises(ValueError, match="exactly 30"):
        AcceptedDiscoveryManifest.model_validate(_resigned(payload))


def test_unknown_manifest_slug_is_rejected_against_corpus() -> None:
    payload = load_accepted_manifest().model_dump(mode="json")
    payload["decisions"][0]["slug"] = "unknown-owner-decision"
    manifest = AcceptedDiscoveryManifest.model_validate(_resigned(payload))

    with pytest.raises(ValueError, match="slugs differ"):
        transfer_owner_accepted_discoveries(
            object(),
            dry_run=True,
            manifest=manifest,  # type: ignore[arg-type]
        )


def test_extra_combined_corpus_is_rejected_before_database_access() -> None:
    corpora = load_all_curated_discovery_corpora()

    with pytest.raises(ValueError, match="exactly 30"):
        transfer_owner_accepted_discoveries(
            object(),  # type: ignore[arg-type]
            dry_run=True,
            corpora=(*corpora, deepcopy(corpora[0])),
        )


def test_worker_output_is_bounded_and_contains_no_sensitive_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = AcceptedTransferSummary(
        created=30,
        transferred=30,
        unchanged=0,
        verified=30,
        dry_run=True,
        corpus_checksum="a" * 64,
        manifest_checksum="b" * 64,
    )

    class SessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(worker, "get_session_factory", lambda: SessionContext)
    monkeypatch.setattr(
        worker, "transfer_owner_accepted_discoveries", lambda *_args, **_kwargs: summary
    )
    monkeypatch.setattr("sys.argv", ["transfer_accepted_discoveries", "--dry-run"])

    worker.main()
    output = capsys.readouterr().out

    assert len(output) < 512
    assert "database_url" not in output.casefold()
    assert "password" not in output.casefold()
    assert "session_secret" not in output.casefold()
    assert "reviewer" not in output.casefold()
