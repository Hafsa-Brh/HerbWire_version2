from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MaterialMediaResponse(BaseModel):
    local_path: str
    source_page: str
    direct_asset_url: str
    creator: str
    title: str
    attribution: str
    license: str
    license_url: str
    checksum_sha256: str
    alt_text: str


class MaterialSectionResponse(BaseModel):
    key: str
    heading: str
    text: str
    source_ids: list[str]


class MaterialSourceResponse(BaseModel):
    id: UUID
    source_name: str
    title: str
    source_type: str
    external_identifier: str
    canonical_url: str
    supported_sections: list[str]


class MaterialStorySummaryResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    deck: str
    category: str
    material_labels: list[str]
    geography_label: str | None
    reading_time_minutes: int
    featured: bool
    published_at: datetime
    hero_media: MaterialMediaResponse


class MaterialStoryDetailResponse(MaterialStorySummaryResponse):
    content_version: int
    sections: list[MaterialSectionResponse]
    sources: list[MaterialSourceResponse]
    related: list[MaterialStorySummaryResponse] = Field(default_factory=list)


class MaterialStoryPageResponse(BaseModel):
    items: list[MaterialStorySummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    categories: list[str]
