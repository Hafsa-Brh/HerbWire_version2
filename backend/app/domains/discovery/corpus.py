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
NEW_PLANT_CORPUS_PATH = Path(__file__).with_name("curated_new_plant_corpus.json")
FINAL_DISCOVERY_CORPUS_PATH = Path(__file__).with_name(
    "curated_final_discovery_corpus.json"
)
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
    source_id: str = Field(pattern=r"^[a-z0-9-]+:[A-Za-z0-9._-]+$")
    provider: Literal["pubmed-eutils", "kew-powo", "nccih", "ema-herbal"] = (
        "pubmed-eutils"
    )
    support_role: Literal[
        "primary_evidence",
        "taxonomy",
        "distribution",
        "taxonomy_distribution",
        "safety",
    ] = "primary_evidence"
    external_identifier: str | None = None
    pmid: str | None = Field(default=None, pattern=r"^\d+$")
    doi: str | None = None
    canonical_url: HttpUrl
    title: str = Field(min_length=20)
    authors: list[str] = []
    journal: str | None = None
    publication_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    publication_types: list[str] = []
    retraction_status: Literal["checked_clear", "not_applicable"] = "checked_clear"

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
        identifier = self.external_identifier or self.pmid
        if not identifier:
            raise ValueError("every source requires an external identifier")
        if self.provider == "pubmed-eutils":
            if not self.pmid or self.source_id != f"pubmed:{self.pmid}":
                raise ValueError("PubMed source_id must match PMID")
            if (
                str(self.canonical_url)
                != f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
            ):
                raise ValueError("canonical_url must be the canonical PubMed record")
            if not self.authors or not self.journal or not self.publication_date:
                raise ValueError("PubMed bibliographic metadata is incomplete")
            if not self.publication_types or self.retraction_status != "checked_clear":
                raise ValueError("PubMed type and retraction checks are required")
        elif self.pmid is not None or self.retraction_status != "not_applicable":
            raise ValueError("non-PubMed sources cannot declare a PMID check")
        return self

    @property
    def stable_identifier(self) -> str:
        return self.external_identifier or self.pmid or ""


class BotanicalIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    common_name: str
    accepted_scientific_name: str
    cited_scientific_name: str | None = None
    family: str
    authority_source_id: str
    authority_taxon_id: str
    authority_url: HttpUrl
    accepted: bool = True


class CuratedMedia(BaseModel):
    model_config = ConfigDict(extra="forbid")
    local_path: str = Field(pattern=r"^/media/discoveries/[a-z0-9-]+\.(?:jpg|png)$")
    source_page: HttpUrl
    direct_asset_url: HttpUrl
    stable_media_identifier: str
    creator: str
    license: str
    license_url: HttpUrl
    attribution: str
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    plant_relevance: str
    classification: Literal[
        "study_specific",
        "documentary",
        "editorial_illustration",
        "botanical_reference",
    ]
    caption: str
    alt_text: str

    @model_validator(mode="after")
    def caption_matches_classification(self):
        if self.classification == "study_specific":
            expected = "Image associated with the reported research."
        elif self.classification == "editorial_illustration":
            expected = (
                "Editorial research illustration; not a photograph of the reported "
                "study."
            )
        elif self.classification == "botanical_reference":
            expected = (
                "Botanical reference image; not an image from the reported study."
            )
        else:
            expected = "Documentary image of "
        if not self.caption.startswith(expected):
            raise ValueError("media caption does not match its policy classification")
        return self


class RichSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z0-9_]+$")
    heading: str
    text: str = Field(min_length=80)
    source_ids: list[str] = Field(min_length=1)
    evidence_locations: list[str] = Field(min_length=1)


class SectionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_ids: list[str] = Field(min_length=1)
    evidence_locations: list[str] = Field(min_length=1)


class CuratedGeography(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country_or_region: str
    iso_country_code: str | None = Field(default=None, min_length=2, max_length=2)
    iso_country_codes: list[str] = []
    geography_kind: Literal["botanical_distribution", "research_geography"] = (
        "research_geography"
    )
    evidence_type: Literal[
        "native_distribution",
        "introduced_distribution",
        "uncertain_distribution",
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

    @field_validator("iso_country_codes")
    @classmethod
    def validate_country_codes(cls, values: list[str]) -> list[str]:
        normalized = [value.upper() for value in values]
        if any(len(value) != 2 or not value.isalpha() for value in normalized):
            raise ValueError("distribution country codes must be ISO alpha-2")
        if len(normalized) != len(set(normalized)):
            raise ValueError("distribution country codes must be unique")
        return normalized


class CuratedDiscovery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_version: int = Field(ge=1)
    content_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    plant_slug: str | None = None
    common_name: str
    scientific_name: str
    botanical_identity: BotanicalIdentity | None = None
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
    additional_sections: list[RichSection] = []
    geography: list[CuratedGeography] = []
    image_caption: (
        Literal["Botanical reference image; not an image from the reported study."]
        | None
    ) = None
    hero_image: CuratedMedia | None = None
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
        if any(
            not set(section.source_ids) <= source_ids
            for section in self.additional_sections
        ):
            raise ValueError("every rich-section source must resolve")
        if len({section.key for section in self.additional_sections}) != len(
            self.additional_sections
        ):
            raise ValueError("rich-section keys must be unique")
        if self.plant_slug is None:
            if self.botanical_identity is None or self.hero_image is None:
                raise ValueError(
                    "standalone discoveries require botanical identity and licensed "
                    "media"
                )
            if self.botanical_identity.authority_source_id not in source_ids:
                raise ValueError("botanical identity authority must resolve")
            if not any(
                item.geography_kind == "botanical_distribution"
                for item in self.geography
            ):
                raise ValueError(
                    "standalone discoveries require botanical distribution"
                )
        elif self.image_caption is None:
            raise ValueError("profile-linked discoveries require an image caption")
        return self

    def calculated_checksum(self) -> str:
        payload = self.model_dump(mode="json", exclude={"content_checksum"})
        if self.plant_slug is not None:
            for key in ("botanical_identity", "additional_sections", "hero_image"):
                payload.pop(key, None)
            for source in payload["sources"]:
                for key in ("provider", "support_role", "external_identifier"):
                    source.pop(key, None)
            for geography in payload["geography"]:
                geography.pop("geography_kind", None)
                geography.pop("iso_country_codes", None)
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class CuratedDiscoveryCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1, 2, 3]
    batch_id: str = "milestone-4b"
    selection_audit: list[dict] = []
    articles: list[CuratedDiscovery]

    @model_validator(mode="after")
    def validate_corpus(self):
        expected_count = {1: 10, 2: 12, 3: 8}[self.schema_version]
        if len(self.articles) != expected_count:
            raise ValueError(
                f"the curated corpus must contain exactly {expected_count} articles"
            )
        for attribute in ("slug", "scientific_name"):
            values = [getattr(article, attribute) for article in self.articles]
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {attribute}")
        pmids = [
            source.pmid
            for article in self.articles
            for source in article.sources
            if source.pmid
        ]
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
        if self.schema_version == 2:
            if self.batch_id != "milestone-4c-new-plants":
                raise ValueError("unexpected Milestone 4C batch identifier")
            if any(article.plant_slug is not None for article in self.articles):
                raise ValueError(
                    "Milestone 4C plants must not link encyclopedia profiles"
                )
            if len(self.selection_audit) < 12:
                raise ValueError("Milestone 4C selection audit is incomplete")
        if self.schema_version == 3:
            if self.batch_id != "milestone-4c-final-eight":
                raise ValueError("unexpected final Milestone 4C batch identifier")
            if len(self.articles) != 8:
                raise ValueError(
                    "the final Milestone 4C corpus must contain eight articles"
                )
            if any(article.plant_slug is not None for article in self.articles):
                raise ValueError("final Milestone 4C plants must be standalone")
            if len(self.selection_audit) < 8:
                raise ValueError("final Milestone 4C selection audit is incomplete")
        return self


def load_curated_discovery_corpus(path: Path = CORPUS_PATH) -> CuratedDiscoveryCorpus:
    return CuratedDiscoveryCorpus.model_validate_json(path.read_text(encoding="utf-8"))


def load_new_plant_discovery_corpus(
    path: Path = NEW_PLANT_CORPUS_PATH,
) -> CuratedDiscoveryCorpus:
    corpus = CuratedDiscoveryCorpus.model_validate_json(
        path.read_text(encoding="utf-8")
    )
    if corpus.schema_version != 2:
        raise ValueError("the new-plant corpus must use schema version 2")
    return corpus


def load_final_discovery_corpus(
    path: Path = FINAL_DISCOVERY_CORPUS_PATH,
) -> CuratedDiscoveryCorpus:
    corpus = CuratedDiscoveryCorpus.model_validate_json(
        path.read_text(encoding="utf-8")
    )
    if corpus.schema_version != 3:
        raise ValueError("the final discovery corpus must use schema version 3")
    return corpus
