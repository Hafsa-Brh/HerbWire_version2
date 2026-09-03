from datetime import datetime, timezone

from backend.app.collectors.providers.base import CollectedDiscoveryRecord
from backend.app.domains.discovery.drafting import DeterministicDiscoveryDraftWriter
from backend.app.domains.discovery.enrichment import DeterministicEvidenceEnricher
from backend.app.domains.discovery.normalization import normalize_doi, normalize_record
from backend.app.domains.discovery.qa import evaluate_draft
from backend.app.domains.discovery.relevance import PlantTerm, detect_relevance


def collected(
    *,
    identifier: str = "39900001",
    title: str = "Safety evidence concerning Zingiber officinale",
    abstract: str = (
        "Zingiber officinale is examined in a small clinical study. "
        "The abstract reports limitations and does not establish efficacy."
    ),
    doi: str | None = "https://doi.org/10.1000/Example.1",
    url: str = "https://pubmed.ncbi.nlm.nih.gov/39900001/?from=test",
) -> CollectedDiscoveryRecord:
    return CollectedDiscoveryRecord(
        external_identifier=identifier,
        url=url,
        canonical_url=url,
        title=title,
        publisher="National Library of Medicine (PubMed)",
        source_type="scientific_literature",
        original_language="eng",
        license_status="PubMed metadata",
        text=abstract,
        doi=doi,
        authors=(" Amina  Researcher ",),
        journal=" Test Journal ",
        publication_date="2026-09-01",
        retrieved_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
        metadata={"publication_types": ["Clinical Study"]},
    )


def plant_terms() -> list[PlantTerm]:
    return [PlantTerm("Ginger", "Zingiber officinale Roscoe")]


def test_normalization_stabilizes_doi_url_whitespace_and_content_hash() -> None:
    normalized = normalize_record(collected())
    same_content_other_identity = normalize_record(
        collected(
            identifier="49900001",
            doi=None,
            url="https://pubmed.ncbi.nlm.nih.gov/49900001/",
        )
    )
    assert normalize_doi("DOI: 10.1000/Example.1") == "10.1000/example.1"
    assert normalized.canonical_url == "https://pubmed.ncbi.nlm.nih.gov/39900001/"
    assert normalized.authors == ("Amina Researcher",)
    assert normalized.journal == "Test Journal"
    assert normalized.content_hash == same_content_other_identity.content_hash


def test_relevance_accepts_supported_binomial_and_rejects_excluded_topics() -> None:
    normalized = normalize_record(collected())
    accepted = detect_relevance(normalized, plant_terms())
    rejected = detect_relevance(
        normalize_record(
            collected(
                title="Acupuncture-only complementary medicine study",
                abstract="Acupuncture trial mentioning ginger only in a survey label.",
            )
        ),
        plant_terms(),
    )
    assert accepted.relevant is True
    assert accepted.entities[0]["scientific_name"] == "Zingiber officinale"
    assert accepted.entities[0]["ambiguous"] is False
    assert accepted.evidence_signals == ("scientific_name:Zingiber officinale",)
    assert rejected.relevant is False
    assert "acupuncture_only" in rejected.reasons


def test_common_name_is_explicitly_ambiguous_and_held_by_qa() -> None:
    normalized = normalize_record(
        collected(
            title="Safety review of ginger preparations",
            abstract="Ginger is discussed as a traditional herbal preparation.",
        )
    )
    decision = detect_relevance(normalized, plant_terms())
    evidence = DeterministicEvidenceEnricher().enrich(normalized, "source-1", decision)
    draft = DeterministicDiscoveryDraftWriter().write(normalized, evidence)
    qa = evaluate_draft(draft, evidence)
    assert decision.relevant is True
    assert decision.entities[0]["ambiguous"] is True
    assert qa.passed is False
    assert "scientific_identity_unambiguous" in qa.reason_codes


def test_evidence_draft_and_qa_are_traceable_and_medically_conservative() -> None:
    normalized = normalize_record(collected())
    decision = detect_relevance(normalized, plant_terms())
    evidence = DeterministicEvidenceEnricher().enrich(normalized, "source-1", decision)
    draft = DeterministicDiscoveryDraftWriter().write(normalized, evidence)
    qa = evaluate_draft(draft, evidence)
    combined = " ".join(
        [draft.standfirst, *(block["text"] for block in draft.body_blocks)]
    ).casefold()

    assert evidence.excerpts[0]["source_record_id"] == "source-1"
    assert evidence.excerpts[0]["location"] == "abstract_sentence:1"
    assert all(
        block["source_record_ids"] == ["source-1"] for block in draft.body_blocks
    )
    assert draft.limitations
    assert draft.safety_context
    assert "take 500 mg" not in combined
    assert "recommended dose" not in combined
    assert "treatment recommendation" in " ".join(draft.cannot_conclude).casefold()
    assert qa.passed is True


def test_missing_supported_excerpt_fails_closed() -> None:
    normalized = normalize_record(collected(abstract=""))
    decision = detect_relevance(normalized, plant_terms())
    evidence = DeterministicEvidenceEnricher().enrich(normalized, "source-1", decision)
    draft = DeterministicDiscoveryDraftWriter().write(normalized, evidence)
    qa = evaluate_draft(draft, evidence)
    assert qa.passed is False
    assert "evidence_excerpt_present" in qa.reason_codes
