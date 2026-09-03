import hashlib
import re
from urllib.parse import urlsplit, urlunsplit

from backend.app.collectors.providers.base import CollectedDiscoveryRecord
from backend.app.domains.discovery.contracts import NormalizedDiscoveryRecord


class NormalizationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_doi(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_whitespace(value).casefold()
    normalized = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", normalized)
    return normalized or None


def normalize_canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme != "https" or not parts.netloc:
        raise NormalizationError(
            "invalid_canonical_url", "Source canonical URL must be HTTPS."
        )
    return urlunsplit((parts.scheme, parts.netloc.casefold(), parts.path, "", ""))


def normalize_record(record: CollectedDiscoveryRecord) -> NormalizedDiscoveryRecord:
    external_identifier = normalize_whitespace(record.external_identifier)
    title = normalize_whitespace(record.title)
    if not external_identifier:
        raise NormalizationError(
            "missing_external_identifier", "Source record identifier is required."
        )
    if not title:
        raise NormalizationError("missing_title", "Source record title is required.")
    if record.original_language.casefold() not in {"en", "eng"}:
        raise NormalizationError(
            "unsupported_language", "Milestone 4A accepts English PubMed records only."
        )

    abstract = normalize_whitespace(record.text) or None
    canonical_url = normalize_canonical_url(record.canonical_url)
    doi = normalize_doi(record.doi)
    hash_input = "\n".join([title, abstract or "", record.journal or ""])
    content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    authors = tuple(
        name for value in record.authors if (name := normalize_whitespace(value))
    )
    return NormalizedDiscoveryRecord(
        external_identifier=external_identifier,
        doi=doi,
        canonical_url=canonical_url,
        title=title,
        abstract=abstract,
        authors=authors,
        journal=normalize_whitespace(record.journal) if record.journal else None,
        publication_date=record.publication_date,
        original_language="en",
        content_hash=content_hash,
        collected_at_iso=record.retrieved_at.isoformat(),
        metadata=dict(record.metadata),
    )
