"""Authenticated API contracts for sequential Plant profile automation."""

from uuid import UUID

from pydantic import BaseModel, Field


class PlantPipelineStartRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=10)
    all_available: bool = False
    idempotency_key: str = Field(min_length=8, max_length=255)


class PlantPipelinePreviewResponse(BaseModel):
    can_start: bool
    unavailable_reason: str | None
    active_pipeline: str | None


class PlantPipelineItemResponse(BaseModel):
    id: UUID
    title: str | None
    status: str
    editorial_status: str | None
    plant_profile_id: UUID | None
    review_id: UUID | None


class PlantPipelineRunResponse(BaseModel):
    id: UUID
    status: str
    items: list[PlantPipelineItemResponse]
