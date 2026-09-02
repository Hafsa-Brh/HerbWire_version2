from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from backend.app.collectors.providers.base import CollectionRequest
from backend.app.collectors.providers.pubmed import (
    PUBMED_QUERY,
    HttpResponse,
    PubMedCollectionError,
    PubMedCollectionProvider,
    PubMedMalformedResponse,
    PubMedProviderConfig,
    PubMedTransientError,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "pubmed"


class QueueTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls: list[str] = []

    def get(self, url: str, timeout_seconds: float) -> HttpResponse:
        assert timeout_seconds == 2
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def response(body: bytes, status: int = 200, **headers: str) -> HttpResponse:
    return HttpResponse(status=status, headers=headers, body=body)


def provider(transport, sleeps=None, *, batch_size=5, retries=2):
    return PubMedCollectionProvider(
        PubMedProviderConfig(
            email="ci-contact@example.invalid",
            timeout_seconds=2,
            max_retries=retries,
            batch_size=batch_size,
            minimum_request_interval_seconds=0,
        ),
        transport=transport,
        sleep=(sleeps.append if sleeps is not None else lambda _: None),
    )


def request(max_records: int = 5) -> CollectionRequest:
    return CollectionRequest(date(2026, 8, 1), date(2026, 9, 1), max_records)


def test_saved_esearch_and_efetch_preserve_pubmed_provenance() -> None:
    transport = QueueTransport(
        [
            response((FIXTURES / "esearch.xml").read_bytes()),
            response((FIXTURES / "efetch.xml").read_bytes()),
        ]
    )

    records = provider(transport).collect(request())

    assert len(records) == 1
    record = records[0]
    assert record.external_identifier == "39900001"
    assert record.doi == "10.1000/HERBWIRE.2026.1"
    assert record.canonical_url == "https://pubmed.ncbi.nlm.nih.gov/39900001/"
    assert record.authors == ("Amina Researcher", "Botanical Evidence Group")
    assert record.journal == "Journal of Botanical Evidence"
    assert record.publication_date == "2026-09-01"
    assert record.original_language == "en"
    assert record.metadata["abstract_status"] == "present"

    query = parse_qs(urlsplit(transport.urls[0]).query)
    assert query["term"] == [PUBMED_QUERY]
    assert query["datetype"] == ["pdat"]
    assert query["mindate"] == ["2026/08/01"]
    assert query["maxdate"] == ["2026/09/01"]
    assert query["tool"] == ["HerbWire"]
    assert query["email"] == ["ci-contact@example.invalid"]


def test_timeout_is_bounded_and_reported_safely() -> None:
    transport = QueueTransport(
        [
            PubMedTransientError("pubmed_transport_error", "safe timeout"),
            PubMedTransientError("pubmed_transport_error", "safe timeout"),
        ]
    )
    with pytest.raises(PubMedTransientError, match="safe timeout"):
        provider(transport, retries=1).collect(request(1))
    assert len(transport.urls) == 2


def test_transient_status_retries_and_honors_retry_after() -> None:
    sleeps: list[float] = []
    transport = QueueTransport(
        [
            response(b"", 429, **{"Retry-After": "2"}),
            response((FIXTURES / "esearch.xml").read_bytes()),
            response((FIXTURES / "efetch.xml").read_bytes()),
        ]
    )
    records = provider(transport, sleeps=sleeps).collect(request(1))
    assert len(records) == 1
    assert sleeps == [2.0]


def test_permanent_status_is_not_retried() -> None:
    transport = QueueTransport([response(b"", 400)])
    with pytest.raises(PubMedCollectionError) as caught:
        provider(transport).collect(request(1))
    assert caught.value.code == "pubmed_permanent_http_error"
    assert len(transport.urls) == 1


@pytest.mark.parametrize(
    "payload", [b"<broken", b"<eSearchResult><Count>x</Count></eSearchResult>"]
)
def test_malformed_esearch_is_rejected(payload: bytes) -> None:
    with pytest.raises(PubMedMalformedResponse):
        provider(QueueTransport([response(payload)])).collect(request(1))


def test_missing_abstract_and_doi_are_distinguished_from_malformed_data() -> None:
    xml = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation>
    <PMID>39900002</PMID><Article><Journal><JournalIssue><PubDate>
    <Year>2026</Year></PubDate></JournalIssue><Title>Test Journal</Title></Journal>
    <ArticleTitle>Herbal record without abstract</ArticleTitle>
    <Language>eng</Language></Article></MedlineCitation><PubmedData>
    <ArticleIdList><ArticleId IdType="pubmed">39900002</ArticleId></ArticleIdList>
    </PubmedData></PubmedArticle></PubmedArticleSet>"""
    transport = QueueTransport(
        [
            response(
                b"<eSearchResult><Count>1</Count><IdList><Id>39900002</Id></IdList></eSearchResult>"
            ),
            response(xml),
        ]
    )
    record = provider(transport).collect(request(1))[0]
    assert record.text == ""
    assert record.doi is None
    assert record.metadata["abstract_status"] == "absent"


def test_bounded_pagination_never_exceeds_requested_maximum() -> None:
    search_one = (
        b"<eSearchResult><Count>2</Count><IdList>"
        b"<Id>39900001</Id></IdList></eSearchResult>"
    )
    search_two = (
        b"<eSearchResult><Count>2</Count><IdList>"
        b"<Id>39900002</Id></IdList></eSearchResult>"
    )
    fetch_one = (FIXTURES / "efetch.xml").read_bytes()
    fetch_two = fetch_one.replace(b"39900001", b"39900002").replace(
        b"10.1000/HERBWIRE.2026.1", b"10.1000/HERBWIRE.2026.2"
    )
    transport = QueueTransport(
        [
            response(search_one),
            response(fetch_one),
            response(search_two),
            response(fetch_two),
        ]
    )
    records = provider(transport, batch_size=1).collect(request(2))
    assert [record.external_identifier for record in records] == [
        "39900001",
        "39900002",
    ]
    starts = [
        parse_qs(urlsplit(url).query)["retstart"][0]
        for url in transport.urls
        if "esearch.fcgi" in url
    ]
    assert starts == ["0", "1"]


def test_collection_request_enforces_window_and_record_bounds() -> None:
    with pytest.raises(ValueError, match="between 1 and 5"):
        CollectionRequest(date(2026, 9, 1), date(2026, 9, 1), 6)
    with pytest.raises(ValueError, match="31 days"):
        CollectionRequest(date(2026, 7, 1), date(2026, 9, 1), 1)
    with pytest.raises(ValueError, match="after"):
        CollectionRequest(date(2026, 9, 2), date(2026, 9, 1), 1)


def test_indexing_window_uses_exact_edat_parameters() -> None:
    transport = QueueTransport(
        [response(b"<eSearchResult><Count>0</Count><IdList /></eSearchResult>")]
    )
    window = CollectionRequest(
        date(2026, 8, 1), date(2026, 8, 2), 1, date_type="indexing"
    )
    assert provider(transport).collect(window) == []
    query = parse_qs(urlsplit(transport.urls[0]).query)
    assert query["datetype"] == ["edat"]
    assert query["mindate"] == ["2026/08/01"]
    assert query["maxdate"] == ["2026/08/02"]
