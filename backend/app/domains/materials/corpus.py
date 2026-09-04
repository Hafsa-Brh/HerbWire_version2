from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

CORPUS_DIR = Path(__file__).with_name("records")


class MaterialSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z0-9_]+$")
    heading: str = Field(min_length=3)
    text: str = Field(min_length=120)
    source_ids: list[str] = Field(min_length=1)


class MaterialSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(pattern=r"^[a-z0-9-]+:[A-Za-z0-9._-]+$")
    provider: str = Field(pattern=r"^[a-z0-9-]+$")
    institution: str
    title: str
    canonical_url: HttpUrl
    source_type: Literal[
        "cultural_heritage",
        "museum_collection",
        "botanical",
        "conservation",
        "forestry",
        "research",
    ]
    publication_date: str | None = None


class MaterialMedia(BaseModel):
    model_config = ConfigDict(extra="forbid")
    local_path: str = Field(pattern=r"^/media/materials/[a-z0-9-]+\.jpg$")
    source_page: HttpUrl
    direct_asset_url: HttpUrl
    creator: str
    title: str
    attribution: str
    license: str
    license_url: HttpUrl
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    alt_text: str = Field(min_length=20)


class CuratedMaterialStory(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_version: int = Field(ge=1)
    title: str = Field(min_length=20)
    deck: str = Field(min_length=80)
    category: Literal[
        "Fibres", "Glass", "Paper", "Pigments & Dyes", "Cork", "Wood", "Clay & Glass"
    ]
    material_labels: list[str] = Field(min_length=1)
    geography_label: str | None = None
    sections: list[MaterialSection] = Field(min_length=6, max_length=9)
    reading_time_minutes: int = Field(ge=4, le=12)
    featured: bool = False
    sort_order: int = Field(ge=1)
    published_at: str
    hero_media: MaterialMedia
    sources: list[MaterialSource] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_traceability(self):
        source_ids = {source.source_id for source in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("source identifiers must be unique within a story")
        if len({section.key for section in self.sections}) != len(self.sections):
            raise ValueError("section keys must be unique")
        if any(not set(section.source_ids) <= source_ids for section in self.sections):
            raise ValueError("every section source must resolve")
        return self

    @property
    def content_checksum(self) -> str:
        encoded = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class CuratedMaterialCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    batch_id: Literal["demo-material-stories"]
    stories: list[CuratedMaterialStory]

    @model_validator(mode="after")
    def validate_corpus(self):
        if len(self.stories) != 7:
            raise ValueError(
                "the curated material corpus must contain exactly seven stories"
            )
        for field in ("id", "slug"):
            values = [getattr(story, field) for story in self.stories]
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate material story {field}")
        if sum(story.featured for story in self.stories) != 1:
            raise ValueError("exactly one material story must be featured")
        return self


def load_curated_material_corpus(path: Path = CORPUS_DIR) -> CuratedMaterialCorpus:
    stories = [
        CuratedMaterialStory.model_validate_json(item.read_text(encoding="utf-8"))
        for item in sorted(path.glob("*.json"))
    ]
    return CuratedMaterialCorpus(
        schema_version=1, batch_id="demo-material-stories", stories=stories
    )
