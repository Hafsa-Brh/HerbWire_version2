from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceRecordResponse(BaseModel):
    id: UUID
    external_identifier: str
    url: str
    canonical_url: str
    title: str
    publisher: str
    source_type: str
    original_language: str
    license_status: str
    supports: dict
    accessed_at: datetime


class PlantListItemResponse(BaseModel):
    id: UUID
    slug: str
    accepted_scientific_name: str
    botanical_author: str
    taxon_identifier: str
    known_synonyms: list
    display_common_name: str
    family_name: str | None
    diversity_tags: list
    summary: str
    status: str
    hero_image: dict
    published_at: datetime | None
    source_count: int
    growth_form: str
    biome: str
    distribution_summary: str
    readiness_status: str
    version: int


class PlantPageResponse(BaseModel):
    items: list[PlantListItemResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PlantDetailResponse(PlantListItemResponse):
    introduction: str
    botanical_description: str
    traditional_uses: list
    parts_used: list
    distribution: list
    preparation: str
    safety_notes: list
    evidence_notes: str
    article_details: dict
    last_reviewed_at: datetime | None
    sources: list[SourceRecordResponse]


class PlantRevisionResponse(BaseModel):
    id: UUID
    plant_profile_id: UUID
    slug: str
    display_common_name: str
    current_version: int
    proposed_version: int
    status: str
    content_checksum: str
    current_content: PlantDetailResponse
    proposed_content: dict
    proposed_sources: list[SourceRecordResponse]
    reviewer_name: str | None
    decision_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None
    promoted_at: datetime | None


class ReviewResponse(BaseModel):
    id: UUID
    content_type: str
    status: str
    reviewer_name: str | None
    decision_reason: str | None
    review_payload: dict
    created_at: datetime
    decided_at: datetime | None
    plant_profile: PlantDetailResponse | None


class DecisionRequest(BaseModel):
    reviewer_name: str = "Local editor"
    reason: str | None = None


class SeedResponse(BaseModel):
    profiles_created: int
    profiles_updated: int
    profiles_protected: int
    profiles_total: int
    source_records_total: int
    source_links_created: int
    revisions_created: int = 0
    revisions_unchanged: int = 0
    older_versions_skipped: int = 0


class PipelineStageResponse(BaseModel):
    name: str
    status: str
    attempt: int
    duration_ms: int
    input_refs: list
    output_refs: list
    error_code: str | None
    error_message: str | None


class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_type: str
    trigger: str
    provider: str
    idempotency_key: str
    status: str
    current_stage: str
    summary: dict
    started_at: datetime
    finished_at: datetime | None
    stages: list[PipelineStageResponse] = []


class LoginRequest(BaseModel):
    email: str
    password: str


class SessionUserResponse(BaseModel):
    initials: str
    label: str
    role: str


class SessionResponse(BaseModel):
    authenticated: bool
    user: SessionUserResponse | None = None


class NewsletterSubscriptionRequest(BaseModel):
    email: str


class NewsletterSubscriptionResponse(BaseModel):
    email: str
    status: str
    created_at: datetime


class AgentMetricResponse(BaseModel):
    name: str
    total_runs: int
    succeeded: int
    failed: int
    held: int
    skipped: int
    average_duration_ms: int
    last_status: str | None
    last_completed_at: datetime | None


class AgentPerformanceResponse(BaseModel):
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    held_runs: int
    auto_published: int
    last_execution: datetime | None
    stages: list[AgentMetricResponse]
