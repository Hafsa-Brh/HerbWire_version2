"""Finite, source-validated candidates for sequential Discovery automation."""

from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.domains.discovery.corpus import CuratedDiscovery
from backend.app.domains.pipeline.media_validation import (
    inspect_raster,
    resolve_pipeline_media_path,
)
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

CATALOG_PATH = Path(__file__).with_name("discovery_pipeline_catalog.json")
PROJECT_ROOT = Path(__file__).resolve().parents[4]
ALLOWED_LICENSES = {
    "CC0 1.0",
    "Public Domain",
    "CC BY 2.0",
    "CC BY 3.0",
    "CC BY 4.0",
    "CC BY-SA 2.0",
    "CC BY-SA 2.5",
    "CC BY-SA 3.0",
    "CC BY-SA 4.0",
}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class PipelineBotanicalSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    common_names: list[str] = Field(min_length=1)
    accepted_scientific_name: str
    botanical_author: str
    taxon_identifier: str
    synonyms: list[str] = Field(default_factory=list)
    authority_url: HttpUrl


class PipelineMediaVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mime_type: str
    width: int = Field(ge=1200)
    height: int = Field(ge=675)

    @model_validator(mode="after")
    def validate_raster(self) -> "PipelineMediaVerification":
        if self.mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(
                "Discovery media MIME type is not an allowed raster format"
            )
        return self


class DiscoveryPipelineCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    catalogue_version: int = Field(ge=1)
    retrieved_at: str
    abstract_extract: str = Field(min_length=20, max_length=500)
    primary_botanical_subject: PipelineBotanicalSubject
    media_verification: PipelineMediaVerification
    article: CuratedDiscovery

    @model_validator(mode="after")
    def validate_source_package(self) -> "DiscoveryPipelineCandidate":
        primary = [
            source
            for source in self.article.sources
            if source.support_role == "primary_evidence"
        ]
        if len(primary) != 1 or primary[0].provider != "pubmed-eutils":
            raise ValueError("each candidate requires one primary PubMed source")
        if self.key != f"pubmed-{primary[0].pmid}":
            raise ValueError("candidate key must be derived from its PMID")
        if self.article.content_checksum != self.article.calculated_checksum():
            raise ValueError("Discovery candidate content checksum mismatch")
        if self.article.plant_slug is not None:
            raise ValueError(
                "pipeline discoveries must introduce a new botanical subject"
            )
        identity = self.article.botanical_identity
        media = self.article.hero_image
        if identity is None or media is None:
            raise ValueError("pipeline discoveries require identity and licensed media")
        subject = self.primary_botanical_subject
        if (
            identity.accepted_scientific_name != subject.accepted_scientific_name
            or identity.authority_taxon_id != subject.taxon_identifier
            or str(identity.authority_url) != str(subject.authority_url)
            or self.article.scientific_name != subject.accepted_scientific_name
            or self.article.common_name not in subject.common_names
        ):
            raise ValueError("Discovery article and primary botanical identity differ")
        if media.classification != "botanical_reference":
            raise ValueError(
                "Discovery media must be a real botanical reference photograph"
            )
        if media.license not in ALLOWED_LICENSES:
            raise ValueError("Discovery media license is not allowlisted")
        if not media.local_path.startswith("/media/discoveries/pipeline-"):
            raise ValueError("Discovery pipeline media must use an isolated path")
        return self

    @property
    def primary_source(self):
        return next(
            source
            for source in self.article.sources
            if source.support_role == "primary_evidence"
        )


class DiscoveryPipelineCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 2
    candidates: list[DiscoveryPipelineCandidate] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def validate_uniqueness(self) -> "DiscoveryPipelineCatalog":
        values = {
            "keys": [item.key for item in self.candidates],
            "slugs": [item.article.slug for item in self.candidates],
            "pmids": [item.primary_source.pmid for item in self.candidates],
            "dois": [item.primary_source.doi for item in self.candidates],
            "urls": [
                str(item.primary_source.canonical_url) for item in self.candidates
            ],
            "checksums": [item.article.content_checksum for item in self.candidates],
            "taxa": [
                item.primary_botanical_subject.taxon_identifier.casefold()
                for item in self.candidates
            ],
        }
        for label, items in values.items():
            present = [item for item in items if item]
            if len(present) != len(set(present)):
                raise ValueError(f"duplicate Discovery candidate {label}")
        return self

    def validate_media_files(
        self, root: Path = PROJECT_ROOT
    ) -> "DiscoveryPipelineCatalog":
        for candidate in self.candidates:
            media = candidate.article.hero_image
            assert media is not None
            try:
                path = resolve_pipeline_media_path(
                    media.local_path,
                    "discoveries",
                    media_roots=(
                        root / "frontend" / "public",
                        root / "frontend" / "dist",
                    ),
                )
            except (FileNotFoundError, ValueError) as error:
                raise ValueError(
                    f"{candidate.key}: media path is missing or unsafe"
                ) from error

            raster = inspect_raster(path)
            verification = candidate.media_verification
            if (raster.mime_type, raster.width, raster.height) != (
                verification.mime_type,
                verification.width,
                verification.height,
            ):
                raise ValueError(f"{candidate.key}: raster metadata mismatch")
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            if checksum != media.checksum_sha256:
                raise ValueError(f"{candidate.key}: media checksum mismatch")
        return self


def load_discovery_pipeline_catalog(
    path: Path = CATALOG_PATH, *, validate_media: bool = True
) -> DiscoveryPipelineCatalog:
    catalog = DiscoveryPipelineCatalog.model_validate_json(
        path.read_text(encoding="utf-8")
    )
    return catalog.validate_media_files() if validate_media else catalog
