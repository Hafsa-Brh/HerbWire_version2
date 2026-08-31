"""Validated access to the curated encyclopedia corpus manifest."""

from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

CORPUS_PATH = Path(__file__).with_name("corpus.json")


class CorpusModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DistributionRegion(CorpusModel):
    code: str
    name: str
    status: str
    level: int = Field(ge=0, le=3)
    map_countries: list[str] = Field(default_factory=list)

    @field_validator("map_countries")
    @classmethod
    def validate_map_countries(cls, value: list[str]) -> list[str]:
        normalized = [country.upper() for country in value]
        if any(len(country) != 2 or not country.isalpha() for country in normalized):
            raise ValueError("map country codes must be ISO 3166-1 alpha-2 values")
        if len(set(normalized)) != len(normalized):
            raise ValueError(
                "map country codes must be unique within a distribution region"
            )
        return normalized

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"native", "introduced", "unknown"}:
            raise ValueError(
                "distribution status must be native, introduced, or unknown"
            )
        return value


class MediaAsset(CorpusModel):
    kind: str = "licensed_photograph"
    source_page: HttpUrl
    original_url: HttpUrl
    local_path: str
    file_title: str
    creator: str
    license: str
    license_url: HttpUrl | None = None
    attribution: str
    checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    width: int = Field(ge=1200)
    height: int = Field(ge=800)
    original_width: int = Field(ge=1200)
    original_height: int = Field(ge=800)
    mime_type: str
    alt_text: str
    caption: str
    downloaded_at: str

    @field_validator("kind")
    @classmethod
    def require_public_article_photograph(cls, value: str) -> str:
        if value != "licensed_photograph":
            raise ValueError("public corpus media must be a licensed photograph")
        return value


class SourceManifest(CorpusModel):
    source_identifier: str
    source_name: str
    base_url: HttpUrl
    external_identifier: str
    url: HttpUrl
    canonical_url: HttpUrl
    title: str
    publisher: str
    source_type: str
    license_status: str
    supports: dict[str, bool]
    support_role: str
    provenance_notes: str
    source_publication_date: str | None = None


class SourceReference(CorpusModel):
    source_id: str
    support_role: str
    supports: list[str]
    provenance_notes: str


class CorpusProfile(CorpusModel):
    batch: str
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    common_name: str
    accepted_scientific_name: str
    botanical_author: str
    family: str
    taxon_status: str
    taxon_identifier: str
    synonyms: list[str]
    diversity_tags: list[str]
    summary: str
    introduction: str
    botanical_description: str
    traditional_uses: list[dict[str, str]]
    parts_used: list[str]
    distribution: list[DistributionRegion]
    distribution_summary: str
    growth_form: str
    biome: str
    preparation: str
    safety_notes: list[dict[str, str]]
    evidence_notes: str
    media: MediaAsset
    source_refs: list[SourceReference]
    content_version: int = Field(ge=1)
    readiness_status: str
    hold_reason: str | None = None

    @field_validator("taxon_status")
    @classmethod
    def accepted_taxon_only(cls, value: str) -> str:
        if value != "accepted":
            raise ValueError("curated corpus profiles must use an accepted taxon")
        return value

    @field_validator("readiness_status")
    @classmethod
    def validate_readiness(cls, value: str) -> str:
        if value not in {"ready_for_review", "held"}:
            raise ValueError("invalid readiness status")
        return value


class CorpusManifest(CorpusModel):
    schema_version: int
    reviewed_on: str
    sources: list[SourceManifest]
    profiles: list[CorpusProfile]

    @field_validator("profiles")
    @classmethod
    def validate_profiles(cls, profiles: list[CorpusProfile]) -> list[CorpusProfile]:
        slugs = [profile.slug for profile in profiles]
        names = [profile.accepted_scientific_name for profile in profiles]
        if len(profiles) < 30:
            raise ValueError("corpus must contain at least 30 profiles")
        if len(slugs) != len(set(slugs)):
            raise ValueError("corpus slugs must be unique")
        if len(names) != len(set(names)):
            raise ValueError("accepted scientific names must be unique")
        return profiles

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, sources: list[SourceManifest]) -> list[SourceManifest]:
        identifiers = [source.external_identifier for source in sources]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("source external identifiers must be unique")
        return sources

    @model_validator(mode="after")
    def validate_cross_record_uniqueness(self) -> "CorpusManifest":
        batch_counts = {
            batch: sum(profile.batch == batch for profile in self.profiles)
            for batch in "ABC"
        }
        if batch_counts != {"A": 10, "B": 10, "C": 10}:
            raise ValueError(
                f"corpus batches must each contain 10 profiles: {batch_counts}"
            )

        canonical_urls = [str(source.canonical_url) for source in self.sources]
        if len(canonical_urls) != len(set(canonical_urls)):
            raise ValueError("source canonical URLs must be unique")

        checksums: dict[str, str] = {}
        for profile in self.profiles:
            checksum = profile.media.checksum_sha256
            if checksum in checksums:
                duplicate_slug = checksums[checksum]
                raise ValueError(
                    f"{profile.slug}.media.checksum_sha256 duplicates {duplicate_slug}"
                )
            checksums[checksum] = profile.slug

            reference_ids = [reference.source_id for reference in profile.source_refs]
            if len(reference_ids) != len(set(reference_ids)):
                raise ValueError(f"{profile.slug}.source_refs contains duplicates")

            regions = [
                (region.code, region.status, region.level)
                for region in profile.distribution
            ]
            if len(regions) != len(set(regions)):
                raise ValueError(f"{profile.slug}.distribution contains duplicates")
        return self

    def validate_source_coverage(self) -> "CorpusManifest":
        source_ids = {source.external_identifier for source in self.sources}
        for profile in self.profiles:
            missing_refs = {
                reference.source_id
                for reference in profile.source_refs
                if reference.source_id not in source_ids
            }
            if missing_refs:
                raise ValueError(
                    f"{profile.slug}: unknown source references {sorted(missing_refs)}"
                )
            support = {
                key for reference in profile.source_refs for key in reference.supports
            }
            required = {"taxonomy", "traditional_use", "safety", "distribution"}
            if not required.issubset(support):
                missing = ", ".join(sorted(required - support))
                raise ValueError(
                    f"{profile.slug}: missing source support for {missing}"
                )
            if not profile.safety_notes or not profile.evidence_notes:
                raise ValueError(
                    f"{profile.slug}: safety and evidence limits are required"
                )
            if len(profile.introduction.split()) < 50:
                raise ValueError(
                    f"{profile.slug}: source-led background must contain at least 50 "
                    "words"
                )
            if len(profile.evidence_notes.split()) < 30:
                raise ValueError(
                    f"{profile.slug}: evidence snapshot must contain at least 30 words"
                )
            if len(profile.preparation.split()) < 25:
                raise ValueError(
                    f"{profile.slug}: preparation context must contain at least 25 "
                    "words"
                )
            if not any(region.map_countries for region in profile.distribution):
                raise ValueError(
                    f"{profile.slug}: verified map country coverage is required"
                )
        return self


def load_corpus(path: Path = CORPUS_PATH) -> CorpusManifest:
    manifest = CorpusManifest.model_validate_json(path.read_text(encoding="utf-8"))
    return manifest.validate_source_coverage()
