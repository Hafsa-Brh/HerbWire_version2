# ruff: noqa: E501
from backend.app.collectors.providers.base import (
    CollectedDiscoveryRecord,
    CollectionProvider,
    CollectionRequest,
)


class FixtureDiscoveryProvider(CollectionProvider):
    name = "fixture"

    def __init__(self, mode: str = "success") -> None:
        self.mode = mode

    def collect(
        self, request: CollectionRequest | None = None
    ) -> list[CollectedDiscoveryRecord]:
        if self.mode == "source_failure":
            raise RuntimeError("fixture source unavailable")
        if self.mode == "malformed":
            return [
                CollectedDiscoveryRecord(
                    external_identifier="fixture-malformed",
                    url="",
                    canonical_url="",
                    title="",
                    publisher="Fixture Source",
                    source_type="discovery_fixture",
                    original_language="en",
                    license_status="fixture use only",
                    text="",
                )
            ]
        if self.mode == "irrelevant":
            return [
                CollectedDiscoveryRecord(
                    external_identifier="fixture-unrelated",
                    url="https://example.org/weather",
                    canonical_url="https://example.org/weather",
                    title="Daily weather note",
                    publisher="Fixture Source",
                    source_type="discovery_fixture",
                    original_language="en",
                    license_status="fixture use only",
                    text="A local weather report with no medicinal plant or traditional medicine relevance.",
                )
            ]
        return [
            CollectedDiscoveryRecord(
                external_identifier="fixture-chamomile-quality-note-2026-08-30",
                url="https://example.org/fixtures/chamomile-quality-note",
                canonical_url="https://example.org/fixtures/chamomile-quality-note",
                title="Fixture note on chamomile source quality review",
                publisher="HerbWire Fixture Source",
                source_type="discovery_fixture",
                original_language="en",
                license_status="Synthetic fixture; safe for tests and local demonstration only.",
                text="A synthetic editorial fixture about medicinal plant source-quality review for chamomile. It is intentionally not public content.",
                plant_hint="German chamomile",
            )
        ]
