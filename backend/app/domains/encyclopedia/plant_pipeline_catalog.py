"""Validated, bounded inputs for sequential Plant profile automation."""

from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.domains.encyclopedia.corpus import CorpusProfile, SourceManifest
from backend.app.domains.pipeline.media_validation import (
    inspect_raster,
    resolve_pipeline_media_path,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

CATALOG_PATH = Path(__file__).with_name("plant_pipeline_catalog.json")
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
REQUIRED_SUPPORT = {
    "taxonomy",
    "traditional_use",
    "evidence",
    "safety",
    "distribution",
    "media",
}


class PipelineCatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlantCandidate(PipelineCatalogModel):
    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    catalogue_version: int = Field(ge=1)
    source_package_key: str
    accepted_scientific_name: str
    botanical_author: str
    taxon_identifier: str
    common_names: list[str] = Field(min_length=1)
    synonyms: list[str] = Field(default_factory=list)


class PlantSourcePackage(PipelineCatalogModel):
    key: str
    collected_at: str
    profile: CorpusProfile
    sources: list[SourceManifest] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_source_led_package(self) -> "PlantSourcePackage":
        source_ids = {source.external_identifier for source in self.sources}
        profile_ids = {reference.source_id for reference in self.profile.source_refs}
        if source_ids != profile_ids:
            raise ValueError("source package and profile references must match exactly")
        support = {
            support_name
            for reference in self.profile.source_refs
            for support_name in reference.supports
        }
        if missing := REQUIRED_SUPPORT - support:
            raise ValueError(f"source package is missing support for {sorted(missing)}")
        if self.profile.media.license not in ALLOWED_LICENSES:
            raise ValueError("media license is not allowlisted")
        if self.profile.media.mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError("media MIME type is not an allowed raster format")
        if self.profile.media.width < 1200 or self.profile.media.height < 675:
            raise ValueError("media is too small for the Plant hero presentation")
        if not self.profile.media.local_path.startswith("/media/plants/pipeline-"):
            raise ValueError("pipeline media must use its isolated public path")
        return self


class PlantPipelineCatalog(PipelineCatalogModel):
    schema_version: int = 1
    candidates: list[PlantCandidate] = Field(min_length=1, max_length=40)
    source_packages: list[PlantSourcePackage] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def validate_catalogue(self) -> "PlantPipelineCatalog":
        package_by_key = {package.key: package for package in self.source_packages}
        if len(package_by_key) != len(self.source_packages):
            raise ValueError("source package keys must be unique")
        candidate_keys = [candidate.key for candidate in self.candidates]
        if len(candidate_keys) != len(set(candidate_keys)):
            raise ValueError("candidate keys must be unique")
        taxon_ids = [
            candidate.taxon_identifier.casefold() for candidate in self.candidates
        ]
        if len(taxon_ids) != len(set(taxon_ids)):
            raise ValueError("candidate taxon identifiers must be unique")
        for candidate in self.candidates:
            package = package_by_key.get(candidate.source_package_key)
            if package is None:
                raise ValueError(f"{candidate.key}: source package is missing")
            profile = package.profile
            if (
                profile.accepted_scientific_name != candidate.accepted_scientific_name
                or profile.botanical_author != candidate.botanical_author
                or profile.taxon_identifier != candidate.taxon_identifier
                or profile.common_name not in candidate.common_names
                or set(profile.synonyms) != set(candidate.synonyms)
            ):
                raise ValueError(
                    f"{candidate.key}: catalogue and source identity differ"
                )
        return self

    def package_for(self, candidate_key: str) -> PlantSourcePackage:
        candidate = next(item for item in self.candidates if item.key == candidate_key)
        return next(
            package
            for package in self.source_packages
            if package.key == candidate.source_package_key
        )

    def validate_media_files(self, root: Path = PROJECT_ROOT) -> "PlantPipelineCatalog":
        for package in self.source_packages:
            media = package.profile.media
            try:
                path = resolve_pipeline_media_path(
                    media.local_path,
                    "plants",
                    media_roots=(
                        root / "frontend" / "public",
                        root / "frontend" / "dist",
                    ),
                )
            except (FileNotFoundError, ValueError) as error:
                raise ValueError(
                    f"{package.key}: media path is missing or unsafe"
                ) from error

            raster = inspect_raster(path)
            if (raster.mime_type, raster.width, raster.height) != (
                media.mime_type,
                media.width,
                media.height,
            ):
                raise ValueError(f"{package.key}: raster metadata mismatch")
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            if checksum != media.checksum_sha256:
                raise ValueError(f"{package.key}: media checksum mismatch")
        return self


def load_plant_pipeline_catalog(
    path: Path = CATALOG_PATH, *, validate_media: bool = True
) -> PlantPipelineCatalog:
    catalog = PlantPipelineCatalog.model_validate_json(path.read_text(encoding="utf-8"))
    return catalog.validate_media_files() if validate_media else catalog
