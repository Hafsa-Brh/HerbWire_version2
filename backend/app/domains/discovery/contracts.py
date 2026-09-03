from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class NormalizedDiscoveryRecord:
    external_identifier: str
    doi: str | None
    canonical_url: str
    title: str
    abstract: str | None
    authors: tuple[str, ...]
    journal: str | None
    publication_date: str | None
    original_language: str
    content_hash: str
    collected_at_iso: str
    metadata: dict


@dataclass(frozen=True)
class RelevanceDecision:
    relevant: bool
    category: str
    confidence: float
    reasons: tuple[str, ...]
    evidence_signals: tuple[str, ...]
    entities: tuple[dict, ...]


@dataclass(frozen=True)
class EvidencePackage:
    source_record_id: str
    source_identifiers: dict
    category: str
    language: str
    evidence_type: str
    entities: tuple[dict, ...]
    excerpts: tuple[dict, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DraftContent:
    slug: str
    headline: str
    standfirst: str
    body_blocks: tuple[dict, ...]
    limitations: tuple[str, ...]
    safety_context: str
    cannot_conclude: tuple[str, ...]

    def checksum_payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class QaDecision:
    passed: bool
    reason_codes: tuple[str, ...]
    checklist: dict[str, bool]


class EvidenceEnrichmentProvider(Protocol):
    name: str

    def enrich(
        self,
        record: NormalizedDiscoveryRecord,
        source_record_id: str,
        decision: RelevanceDecision,
    ) -> EvidencePackage: ...


class DiscoveryDraftWriter(Protocol):
    name: str

    def write(
        self, record: NormalizedDiscoveryRecord, evidence: EvidencePackage
    ) -> DraftContent: ...
