from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    promotion_eligible: bool
    promotion_error_code: str | None
    promotion_error_message: str | None
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
    model_config = ConfigDict(from_attributes=True)

    name: str
    status: str
    attempt: int
    duration_ms: int
    input_count: int = 0
    output_count: int = 0
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


class DiscoveryRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(default="pubmed", pattern="^pubmed$")
    start_date: date
    end_date: date
    max_records: int = Field(default=5, ge=1, le=5)
    date_type: Literal["publication", "indexing"] = "publication"

    @model_validator(mode="after")
    def validate_window(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if (self.end_date - self.start_date).days > 31:
            raise ValueError("date window must not exceed 31 days")
        return self


class DiscoverySourceResponse(BaseModel):
    id: UUID
    provider: str
    support_role: str
    external_identifier: str
    pmid: str | None
    doi: str | None
    canonical_url: str
    title: str
    authors: list
    journal: str | None
    publication_date: str | None


class DiscoveryPlantResponse(BaseModel):
    id: UUID
    slug: str
    common_name: str
    scientific_name: str


class DiscoveryArticleResponse(BaseModel):
    id: UUID
    slug: str
    status: str
    headline: str
    standfirst: str
    body_blocks: list
    limitations: list
    safety_context: str
    cannot_conclude: list
    qa_payload: dict
    version: int
    content_origin: str
    article_type: str | None
    research_date: str | None
    research_question: str | None
    research_context: str | None
    study_design: str | None
    evidence_base: str | None
    intervention: str | None
    comparator: str | None
    main_findings: list
    evidence_strength: str | None
    evidence_strength_rationale: str | None
    why_matters: str | None
    practical_interpretation: str | None
    section_sources: dict
    hero_image: dict
    geography: list
    linked_plants: list[DiscoveryPlantResponse]
    botanical_identity: dict | None
    category: str
    relevance_reasons: list
    detected_entities: list
    evidence_package: dict
    sources: list[DiscoverySourceResponse]
    review_id: UUID | None
    review_status: str | None
    reviewer_name: str | None
    decision_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None
    published_at: datetime | None


class DiscoveryArticlePageResponse(BaseModel):
    items: list[DiscoveryArticleResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PublicDiscoveryArticleResponse(BaseModel):
    id: UUID
    slug: str
    headline: str
    standfirst: str
    body_blocks: list
    limitations: list
    safety_context: str
    cannot_conclude: list
    version: int
    article_type: str | None
    research_date: str | None
    research_question: str | None
    research_context: str | None
    study_design: str | None
    evidence_base: str | None
    intervention: str | None
    comparator: str | None
    main_findings: list
    evidence_strength: str | None
    evidence_strength_rationale: str | None
    why_matters: str | None
    practical_interpretation: str | None
    section_sources: dict
    hero_image: dict
    geography: list
    linked_plants: list[DiscoveryPlantResponse]
    botanical_identity: dict | None
    category: str
    sources: list[DiscoverySourceResponse]
    created_at: datetime
    published_at: datetime


class PublicDiscoveryArticlePageResponse(BaseModel):
    items: list[PublicDiscoveryArticleResponse]
    total: int
    page: int
    page_size: int
    pages: int
