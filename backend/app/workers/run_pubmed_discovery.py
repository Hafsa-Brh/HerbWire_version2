"""Run one bounded PubMed discovery pipeline through the shared orchestrator."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from backend.app.collectors.providers.base import CollectionRequest
from backend.app.collectors.providers.pubmed import (
    HttpResponse,
    PubMedCollectionProvider,
    PubMedProviderConfig,
)
from backend.app.core.settings import get_settings
from backend.app.db.session import get_session_factory
from backend.app.domains.discovery.service import run_discovery_pipeline


class SavedPubMedTransport:
    """Return saved ESearch/EFetch XML without permitting network access."""

    def __init__(self, fixture_directory: Path) -> None:
        self.fixture_directory = fixture_directory

    def get(self, url: str, timeout_seconds: float) -> HttpResponse:
        del timeout_seconds
        endpoint = Path(urlsplit(url).path).name
        fixture_name = {
            "esearch.fcgi": "esearch.xml",
            "efetch.fcgi": "efetch.xml",
        }.get(endpoint)
        if fixture_name is None:
            raise RuntimeError("Unexpected PubMed fixture endpoint.")
        return HttpResponse(
            status=200,
            body=(self.fixture_directory / fixture_name).read_bytes(),
            headers={},
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create review-ready PubMed discovery drafts; never publish them."
    )
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--max-records", type=int, default=5, choices=range(1, 6))
    parser.add_argument(
        "--date-type", choices=("publication", "indexing"), default="publication"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--live",
        action="store_true",
        help="Explicitly opt into the official NCBI E-utilities network.",
    )
    source.add_argument(
        "--fixture-directory",
        type=Path,
        help="Read esearch.xml and efetch.xml from a local fixture directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    request = CollectionRequest(
        args.start_date, args.end_date, args.max_records, args.date_type
    )
    settings = get_settings()
    if args.live:
        provider = PubMedCollectionProvider(
            PubMedProviderConfig(
                email=settings.ncbi_email or "",
                timeout_seconds=settings.ncbi_request_timeout_seconds,
                max_retries=settings.ncbi_max_retries,
            )
        )
        trigger = "manual_cli_live"
    else:
        provider = PubMedCollectionProvider(
            PubMedProviderConfig(
                email="fixture-test@example.invalid",
                minimum_request_interval_seconds=0,
            ),
            transport=SavedPubMedTransport(args.fixture_directory),
        )
        trigger = "manual_cli_fixture"

    with get_session_factory()() as session:
        run = run_discovery_pipeline(session, request, provider, trigger=trigger)
    print(
        json.dumps(
            {"run_id": str(run.id), "status": run.status, "summary": run.summary},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
