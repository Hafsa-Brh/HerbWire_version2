from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Literal, Protocol


@dataclass(frozen=True)
class CollectionRequest:
    start_date: date
    end_date: date
    max_records: int
    date_type: Literal["publication", "indexing"] = "publication"

    def __post_init__(self) -> None:
        if self.date_type not in {"publication", "indexing"}:
            raise ValueError("date_type must be publication or indexing")
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if not 1 <= self.max_records <= 5:
            raise ValueError("max_records must be between 1 and 5")
        if (self.end_date - self.start_date).days > 31:
            raise ValueError("date window must not exceed 31 days")


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
    doi: str | None = None
    authors: tuple[str, ...] = ()
    journal: str | None = None
    publication_date: str | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


class CollectionProvider(Protocol):
    name: str

    def collect(
        self, request: CollectionRequest | None = None
    ) -> list[CollectedDiscoveryRecord]:
        """Return a bounded provider batch for downstream normalization."""
