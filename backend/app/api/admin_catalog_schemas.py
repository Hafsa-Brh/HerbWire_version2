from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminContentSummaryResponse(BaseModel):
    total_content: int
    published_plants: int
    published_discoveries: int
    published_materials: int
    source_records: int
    provenance_relationships: int
    needs_review: int


class AdminContentItemResponse(BaseModel):
    id: UUID
    title: str
    content_type: Literal["plant_profile", "discovery", "material_story"]
    content_type_label: str
    status: str
    timestamp: datetime
    plant_identity: str
    source_count: int
    origin: str
    public_path: str
    editorial_path: str
    pmid: str | None = None


class AdminContentPageResponse(BaseModel):
    summary: AdminContentSummaryResponse
    items: list[AdminContentItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    statuses: list[str] = Field(default_factory=list)


class AdminSourceAssociationResponse(BaseModel):
    content_id: UUID
    content_type: Literal["plant_profile", "discovery", "material_story"]
    title: str
    internal_path: str


class AdminSourceItemResponse(BaseModel):
    id: UUID
    source_name: str
    source_type: str
    authoritative_domain: str
    external_identifier: str
    doi: str | None
    title: str
    publisher: str
    provenance_roles: list[str]
    linked_content_count: int
    associated_content: list[AdminSourceAssociationResponse]
    created_at: datetime
    external_url: str


class AdminSourcePageResponse(BaseModel):
    items: list[AdminSourceItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    source_count: int
    source_record_count: int
    source_types: list[str] = Field(default_factory=list)
