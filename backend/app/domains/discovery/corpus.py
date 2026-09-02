from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

CORPUS_PATH = Path(__file__).with_name("curated_corpus.json")
REQUIRED_SECTIONS = {
    "overview",
    "research_question",
    "why_studied",
    "methods",
    "evidence_base",
    "findings",
    "why_matters",
    "evidence_strength",
    "limitations",
    "safety",
    "cannot_conclude",
}


class CuratedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(pattern=r"^pubmed:\d+$")
    pmid: str = Field(pattern=r"^\d+$")
    doi: str | None = None
    canonical_url: HttpUrl
    title: str = Field(min_length=20)
    authors: list[str] = Field(min_length=1)
    journal: str = Field(min_length=2)
    publication_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    publication_types: list[str] = Field(min_length=1)
    retraction_status: Literal["checked_clear"]

    @field_validator("doi")
    @classmethod
    def normalize_doi(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = (
            value.strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")
        )
        if not normalized.startswith("10.") or "/" not in normalized:
            raise ValueError("DOI must be normalized")
        return normalized

    @model_validator(mode="after")
    def identifiers_match(self):
        if self.source_id != f"pubmed:{self.pmid}":
            raise ValueError("source_id must match PMID")
        if str(self.canonical_url) != f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/":
            raise ValueError("canonical_url must be the canonical PubMed record")
        return self


class SectionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_ids: list[str] = Field(min_length=1)
    evidence_locations: list[str] = Field(min_length=1)


class CuratedGeography(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country_or_region: str
    iso_country_code: str | None = Field(default=None, min_length=2, max_length=2)
    evidence_type: Literal[
        "study_site",
        "participant_location",
        "trial_location",
        "research_institution",
        "author_affiliation",
        "review_coverage",
    ]
    source_id: str
    supporting_text_location: str
    confidence: Literal["high", "qualified"]
    qualification: str
    display_label: str
    map_title: str


class CuratedDiscovery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_version: int = Field(ge=1)
    content_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    plant_slug: str
    common_name: str
    scientific_name: str
    headline: str = Field(min_length=20)
    standfirst: str = Field(min_length=50)
    publication_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    research_date: str | None = None
    article_type: str
    research_question: str
    research_context: str
    study_design: str
    evidence_base: str
    intervention: str | None = None
    comparator: str | None = None
    main_findings: list[str] = Field(min_length=1)
    evidence_strength: Literal["limited", "low", "moderate", "mixed"]
    evidence_strength_rationale: str
    why_matters: str
    limitations: list[str] = Field(min_length=1)
    safety_context: str
    cannot_conclude: list[str] = Field(min_length=1)
    practical_interpretation: str
    section_sources: dict[str, SectionTrace]
    geography: list[CuratedGeography] = []
    image_caption: Literal[
        "Botanical reference image; not an image from the reported study."
    ]
    sources: list[CuratedSource] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_traceability(self):
        source_ids = {source.source_id for source in self.sources}
        if set(self.section_sources) != REQUIRED_SECTIONS:
            raise ValueError("all curated article sections are required exactly once")
        if any(
            not set(trace.source_ids) <= source_ids
            for trace in self.section_sources.values()
        ):
            raise ValueError("every section source must resolve")
        if any(item.source_id not in source_ids for item in self.geography):
            raise ValueError("every geography source must resolve")
        return self

    def calculated_checksum(self) -> str:
        payload = self.model_dump(mode="json", exclude={"content_checksum"})
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class CuratedDiscoveryCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    articles: list[CuratedDiscovery]

    @model_validator(mode="after")
    def validate_corpus(self):
        if len(self.articles) != 10:
            raise ValueError(
                "the Milestone 4B corpus must contain exactly ten articles"
            )
        for attribute in ("slug", "plant_slug"):
            values = [getattr(article, attribute) for article in self.articles]
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {attribute}")
        pmids = [source.pmid for article in self.articles for source in article.sources]
        urls = [
            str(source.canonical_url)
            for article in self.articles
            for source in article.sources
        ]
        dois = [
            source.doi
            for article in self.articles
            for source in article.sources
            if source.doi
        ]
        if (
            len(pmids) != len(set(pmids))
            or len(urls) != len(set(urls))
            or len(dois) != len(set(dois))
        ):
            raise ValueError(
                "source identifiers must be unique across curated discoveries"
            )
        mismatched = [
            article.slug
            for article in self.articles
            if article.content_checksum != article.calculated_checksum()
        ]
        if mismatched:
            raise ValueError(f"content checksum mismatch: {', '.join(mismatched)}")
        return self


def load_curated_discovery_corpus(path: Path = CORPUS_PATH) -> CuratedDiscoveryCorpus:
    return CuratedDiscoveryCorpus.model_validate_json(path.read_text(encoding="utf-8"))
