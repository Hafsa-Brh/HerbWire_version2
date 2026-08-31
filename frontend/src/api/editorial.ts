import { requestJson, type ApiPlantDetail } from "./plants"

export type ApiReview = {
  id: string
  content_type: string
  status: string
  reviewer_name: string | null
  decision_reason: string | null
  review_payload: Record<string, unknown>
  created_at: string
  decided_at: string | null
  plant_profile: ApiPlantDetail | null
}

export type ApiRevisionContent = Pick<ApiPlantDetail,
  | "accepted_scientific_name"
  | "botanical_author"
  | "taxon_identifier"
  | "known_synonyms"
  | "display_common_name"
  | "family_name"
  | "diversity_tags"
  | "summary"
  | "introduction"
  | "botanical_description"
  | "traditional_uses"
  | "parts_used"
  | "distribution"
  | "distribution_summary"
  | "growth_form"
  | "biome"
  | "preparation"
  | "safety_notes"
  | "evidence_notes"
  | "readiness_status"
  | "hero_image"
> & { readiness_reason?: string | null }

export type ApiPlantRevision = {
  id: string
  plant_profile_id: string
  slug: string
  display_common_name: string
  current_version: number
  proposed_version: number
  status: "needs_review" | "approved" | "held" | "promoted" | "superseded"
  content_checksum: string
  current_content: ApiPlantDetail
  proposed_content: ApiRevisionContent
  proposed_sources: ApiPlantDetail["sources"]
  reviewer_name: string | null
  decision_reason: string | null
  created_at: string
  reviewed_at: string | null
  promoted_at: string | null
}
export type ApiPipelineStage = {
  name: string
  status: string
  attempt: number
  duration_ms: number
  input_refs: unknown[]
  output_refs: unknown[]
  error_code: string | null
  error_message: string | null
}

export type ApiPipelineRun = {
  id: string
  pipeline_type: string
  trigger: string
  provider: string
  idempotency_key: string
  status: string
  current_stage: string
  summary: Record<string, unknown>
  started_at: string
  finished_at: string | null
  stages: ApiPipelineStage[]
}

export type ApiAgentMetric = {
  name: string
  total_runs: number
  succeeded: number
  failed: number
  held: number
  skipped: number
  average_duration_ms: number
  last_status: string | null
  last_completed_at: string | null
}

export type ApiAgentPerformance = {
  total_runs: number
  succeeded_runs: number
  failed_runs: number
  held_runs: number
  auto_published: number
  last_execution: string | null
  stages: ApiAgentMetric[]
}

export function fetchReviews(signal?: AbortSignal): Promise<ApiReview[]> {
  return requestJson<ApiReview[]>("/api/v1/admin/reviews", { signal })
}

export function approveReview(reviewId: string): Promise<ApiReview> {
  return requestJson<ApiReview>(`/api/v1/admin/reviews/${reviewId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_name: "Local editor" }),
  })
}

export function rejectReview(reviewId: string, reason: string): Promise<ApiReview> {
  return requestJson<ApiReview>(`/api/v1/admin/reviews/${reviewId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_name: "Local editor", reason }),
  })
}

export function publishPlant(plantId: string): Promise<ApiPlantDetail> {
  return requestJson<ApiPlantDetail>(`/api/v1/admin/plants/${plantId}/publish`, { method: "POST" })
}


export function fetchPlantRevisions(signal?: AbortSignal): Promise<ApiPlantRevision[]> {
  return requestJson<ApiPlantRevision[]>("/api/v1/admin/revisions", { signal })
}

export function approvePlantRevision(revisionId: string): Promise<ApiPlantRevision> {
  return requestJson<ApiPlantRevision>(`/api/v1/admin/revisions/${revisionId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_name: "Local editor" }),
  })
}

export function holdPlantRevision(revisionId: string, reason: string): Promise<ApiPlantRevision> {
  return requestJson<ApiPlantRevision>(`/api/v1/admin/revisions/${revisionId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_name: "Local editor", reason }),
  })
}

export function promotePlantRevision(revisionId: string): Promise<ApiPlantRevision> {
  return requestJson<ApiPlantRevision>(`/api/v1/admin/revisions/${revisionId}/promote`, {
    method: "POST",
  })
}

export function fetchPipelineRuns(signal?: AbortSignal): Promise<ApiPipelineRun[]> {
  return requestJson<ApiPipelineRun[]>("/api/v1/admin/pipeline/runs", { signal })
}

export function fetchAgentPerformance(signal?: AbortSignal): Promise<ApiAgentPerformance> {
  return requestJson<ApiAgentPerformance>("/api/v1/admin/agent-performance", { signal })
}
