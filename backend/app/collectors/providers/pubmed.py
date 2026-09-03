from __future__ import annotations

import socket
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date as calendar_date
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.collectors.providers.base import (
    CollectedDiscoveryRecord,
    CollectionProvider,
    CollectionRequest,
)

PUBMED_QUERY = """(
\"Plants, Medicinal\"[MeSH Terms]
OR \"Phytotherapy\"[MeSH Terms]
OR \"herbal medicine\"[Title/Abstract]
OR \"medicinal plant\"[Title/Abstract]
OR \"medicinal plants\"[Title/Abstract]
OR phytotherap*[Title/Abstract]
OR ethnopharmacolog*[Title/Abstract]
)
AND english[Language]"""
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
MAX_ABSTRACT_CHARACTERS = 6000


class PubMedCollectionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PubMedTransientError(PubMedCollectionError):
    pass


class PubMedMalformedResponse(PubMedCollectionError):
    pass


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport(Protocol):
    def get(self, url: str, timeout_seconds: float) -> HttpResponse: ...


class UrllibHttpTransport:
    def get(self, url: str, timeout_seconds: float) -> HttpResponse:
        request = Request(url, headers={"User-Agent": "HerbWire/0.1 PubMed collector"})
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return HttpResponse(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=response.read(),
                )
        except HTTPError as error:
            return HttpResponse(
                status=error.code,
                headers=dict(error.headers.items()) if error.headers else {},
                body=b"",
            )
        except (URLError, TimeoutError, socket.timeout) as error:
            raise PubMedTransientError(
                "pubmed_transport_error",
                "PubMed could not be reached within the configured timeout.",
            ) from error


@dataclass(frozen=True)
class PubMedProviderConfig:
    email: str
    tool: str = "HerbWire"
    timeout_seconds: float = 10.0
    max_retries: int = 2
    batch_size: int = 5
    minimum_request_interval_seconds: float = 0.34

    def __post_init__(self) -> None:
        if not self.email.strip() or "@" not in self.email:
            raise ValueError(
                "A valid NCBI contact email is required for live collection"
            )
        if not 0 < self.timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 0 and 30")
        if not 0 <= self.max_retries <= 3:
            raise ValueError("max_retries must be between 0 and 3")
        if not 1 <= self.batch_size <= 5:
            raise ValueError("batch_size must be between 1 and 5")
        if self.minimum_request_interval_seconds < 0:
            raise ValueError("minimum request interval must not be negative")


class PubMedCollectionProvider(CollectionProvider):
    name = "pubmed"

    def __init__(
        self,
        config: PubMedProviderConfig,
        transport: HttpTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibHttpTransport()
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at: float | None = None

    def collect(
        self, request: CollectionRequest | None = None
    ) -> list[CollectedDiscoveryRecord]:
        if request is None:
            raise ValueError("PubMed collection requires an explicit bounded request")

        records: list[CollectedDiscoveryRecord] = []
        retstart = 0
        total_matches: int | None = None
        while len(records) < request.max_records:
            batch_size = min(self.config.batch_size, request.max_records - len(records))
            search_xml = self._request(
                "esearch.fcgi",
                {
                    "db": "pubmed",
                    "term": PUBMED_QUERY,
                    "datetype": {
                        "publication": "pdat",
                        "indexing": "edat",
                    }[request.date_type],
                    "mindate": request.start_date.strftime("%Y/%m/%d"),
                    "maxdate": request.end_date.strftime("%Y/%m/%d"),
                    "retstart": str(retstart),
                    "retmax": str(batch_size),
                    "retmode": "xml",
                    "sort": "pub date",
                },
            )
            ids, total_matches = self._parse_search(search_xml)
            if not ids:
                break
            fetch_xml = self._request(
                "efetch.fcgi",
                {
                    "db": "pubmed",
                    "id": ",".join(ids),
                    "retmode": "xml",
                },
            )
            records.extend(self._parse_fetch(fetch_xml))
            retstart += len(ids)
            if retstart >= total_matches:
                break
        return records[: request.max_records]

    def _identified_url(self, endpoint: str, parameters: dict[str, str]) -> str:
        identified = {
            **parameters,
            "tool": self.config.tool,
            "email": self.config.email,
        }
        return f"{EUTILS_BASE_URL}/{endpoint}?{urlencode(identified)}"

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at is not None:
            elapsed = self._monotonic() - self._last_request_at
            remaining = self.config.minimum_request_interval_seconds - elapsed
            if remaining > 0:
                self._sleep(remaining)

    def _request(self, endpoint: str, parameters: dict[str, str]) -> bytes:
        url = self._identified_url(endpoint, parameters)
        for attempt in range(self.config.max_retries + 1):
            self._wait_for_rate_limit()
            try:
                response = self.transport.get(url, self.config.timeout_seconds)
            except PubMedTransientError:
                self._last_request_at = self._monotonic()
                if attempt >= self.config.max_retries:
                    raise
                self._sleep(0.5 * (2**attempt))
                continue
            self._last_request_at = self._monotonic()
            if response.status == 200:
                return response.body
            if response.status not in TRANSIENT_STATUS_CODES:
                raise PubMedCollectionError(
                    "pubmed_permanent_http_error",
                    f"PubMed returned non-retryable HTTP status {response.status}.",
                )
            if attempt >= self.config.max_retries:
                raise PubMedTransientError(
                    "pubmed_transient_http_error",
                    "PubMed remained unavailable after bounded retries.",
                )
            retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
            self._sleep(retry_after if retry_after is not None else 0.5 * (2**attempt))
        raise AssertionError("bounded retry loop exited unexpectedly")

    @staticmethod
    def _parse_search(payload: bytes) -> tuple[list[str], int]:
        try:
            root = ET.fromstring(payload)
            count = int(root.findtext("Count", default="0"))
            ids = [
                value
                for node in root.findall("./IdList/Id")
                if (value := (node.text or "").strip()).isdigit()
            ]
        except (ET.ParseError, ValueError) as error:
            raise PubMedMalformedResponse(
                "pubmed_malformed_search",
                "PubMed ESearch returned malformed XML.",
            ) from error
        return ids, count

    @staticmethod
    def _parse_fetch(payload: bytes) -> list[CollectedDiscoveryRecord]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as error:
            raise PubMedMalformedResponse(
                "pubmed_malformed_fetch",
                "PubMed EFetch returned malformed XML.",
            ) from error

        records: list[CollectedDiscoveryRecord] = []
        for item in root.findall("./PubmedArticle"):
            records.append(_parse_pubmed_article(item))
        return records


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    stripped = value.strip()
    if stripped.isdigit():
        return min(float(stripped), 30.0)
    try:
        retry_at = parsedate_to_datetime(stripped)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(
            0.0, min((retry_at - datetime.now(timezone.utc)).total_seconds(), 30.0)
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def _publication_date(article: ET.Element) -> str | None:
    date_node = article.find("./MedlineCitation/Article/ArticleDate")
    if date_node is None:
        date_node = article.find(
            "./MedlineCitation/Article/Journal/JournalIssue/PubDate"
        )
    if date_node is None:
        return None
    year = (date_node.findtext("Year") or "").strip()
    month = (date_node.findtext("Month") or "").strip()
    day = (date_node.findtext("Day") or "").strip()
    if year.isdigit():
        if not month:
            return year
        month_number = _month_number(month)
        if month_number is None:
            return year
        if not day:
            return f"{year}-{month_number:02d}"
        if not day.isdigit():
            raise PubMedMalformedResponse(
                "pubmed_malformed_date", "PubMed returned a malformed publication day."
            )
        try:
            return calendar_date(int(year), month_number, int(day)).isoformat()
        except ValueError as error:
            raise PubMedMalformedResponse(
                "pubmed_malformed_date", "PubMed returned an invalid publication date."
            ) from error
    medline_date = _node_text(date_node.find("MedlineDate"))
    return medline_date or None


def _month_number(value: str | None) -> int | None:
    if value and value.isdigit():
        number = int(value)
        return number if 1 <= number <= 12 else None
    names = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    return names.get((value or "").strip().casefold()[:3])


def _parse_pubmed_article(item: ET.Element) -> CollectedDiscoveryRecord:
    pmid = _node_text(item.find("./MedlineCitation/PMID"))
    title = _node_text(item.find("./MedlineCitation/Article/ArticleTitle"))
    if not pmid.isdigit() or not title:
        raise PubMedMalformedResponse(
            "pubmed_malformed_record",
            "A PubMed record omitted its required PMID or title.",
        )

    abstract_parts: list[str] = []
    for abstract_node in item.findall(
        "./MedlineCitation/Article/Abstract/AbstractText"
    ):
        text = _node_text(abstract_node)
        if not text:
            continue
        label = (abstract_node.attrib.get("Label") or "").strip()
        abstract_parts.append(f"{label}: {text}" if label else text)
    abstract = " ".join(abstract_parts).strip()
    abstract_was_truncated = len(abstract) > MAX_ABSTRACT_CHARACTERS
    abstract = abstract[:MAX_ABSTRACT_CHARACTERS].rstrip()

    doi = None
    for identifier in item.findall("./PubmedData/ArticleIdList/ArticleId"):
        if identifier.attrib.get("IdType", "").casefold() == "doi":
            doi = _node_text(identifier) or None
            break

    authors: list[str] = []
    for author in item.findall("./MedlineCitation/Article/AuthorList/Author"):
        collective = _node_text(author.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        given = _node_text(author.find("ForeName"))
        family = _node_text(author.find("LastName"))
        name = " ".join(part for part in (given, family) if part)
        if name:
            authors.append(name)

    languages = [
        _node_text(node).casefold()
        for node in item.findall("./MedlineCitation/Article/Language")
    ]
    language = "en" if "eng" in languages else (languages[0] if languages else "")
    publication_types = [
        _node_text(node)
        for node in item.findall(
            "./MedlineCitation/Article/PublicationTypeList/PublicationType"
        )
        if _node_text(node)
    ]
    journal = _node_text(item.find("./MedlineCitation/Article/Journal/Title")) or None
    canonical_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return CollectedDiscoveryRecord(
        external_identifier=pmid,
        url=canonical_url,
        canonical_url=canonical_url,
        title=title,
        publisher="National Library of Medicine (PubMed)",
        source_type="scientific_literature",
        original_language=language,
        license_status="PubMed metadata; abstract copyright remains with its holder.",
        text=abstract,
        doi=doi,
        authors=tuple(authors),
        journal=journal,
        publication_date=_publication_date(item),
        metadata={
            "pmid": pmid,
            "publication_types": publication_types,
            "abstract_status": "present" if abstract else "absent",
            "abstract_truncated": abstract_was_truncated,
            "provider": "pubmed_efetch_xml",
        },
    )
