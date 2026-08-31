from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CollectedDiscoveryRecord:
    external_identifier: str
    url: str
    canonical_url: str
    title: str
    publisher: str
    source_type: str
    original_language: str
    license_status: str
    text: str
    plant_hint: str | None = None


class CollectionProvider(Protocol):
    name: str

    def collect(self) -> list[CollectedDiscoveryRecord]:
        """Return bounded, normalized collection envelopes for ingestion."""
