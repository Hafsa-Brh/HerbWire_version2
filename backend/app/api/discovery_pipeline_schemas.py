"""Authenticated API contracts for sequential Discovery automation."""

from uuid import UUID

from pydantic import BaseModel, Field


class DiscoveryPipelineStartRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=10)
    all_available: bool = False
    idempotency_key: str = Field(min_length=8, max_length=255)


class DiscoveryPipelinePreviewResponse(BaseModel):
    can_start: bool
    unavailable_reason: str | None
    active_pipeline: str | None


class DiscoveryPipelineItemResponse(BaseModel):
    id: UUID
    title: str | None
    status: str
    editorial_status: str | None
    discovery_article_id: UUID | None
    review_id: UUID | None


class DiscoveryPipelineRunResponse(BaseModel):
    id: UUID
    status: str
    items: list[DiscoveryPipelineItemResponse]
