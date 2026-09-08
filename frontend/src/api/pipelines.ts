import { requestJson } from "./plants"

export type PipelineAvailability = {
  can_start: boolean
  unavailable_reason: string | null
  active_pipeline: "plants" | "discoveries" | "pubmed" | null
}

export type GenerationItem = {
  id: string
  title: string | null
  status: "pending" | "running" | "succeeded" | "failed" | "held"
  editorial_status: string | null
  plant_profile_id?: string | null
  discovery_article_id?: string | null
  review_id: string | null
}

export type GenerationRun = {
  id: string
  status: "running" | "succeeded" | "failed" | "held" | "partial"
  items: GenerationItem[]
}

export type PipelineApi = {
  availability: (
    count: number,
    allAvailable: boolean,
    signal?: AbortSignal,
  ) => Promise<PipelineAvailability>
  read: (runId: string, signal?: AbortSignal) => Promise<GenerationRun>
  start: (
    count: number,
    idempotencyKey: string,
    allAvailable: boolean,
  ) => Promise<GenerationRun>
  retry: (runId: string) => Promise<GenerationRun>
}

function pipelineApi(prefix: string): PipelineApi {
  return {
    availability(count, allAvailable, signal) {
      return requestJson<PipelineAvailability>(
        `${prefix}/preview?count=${count}&all_available=${allAvailable}`,
        { signal },
      )
    },
    read(runId, signal) {
      return requestJson<GenerationRun>(`${prefix}/runs/${runId}`, { signal })
    },
    start(count, idempotencyKey, allAvailable) {
      return requestJson<GenerationRun>(`${prefix}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          count,
          all_available: allAvailable,
          idempotency_key: idempotencyKey,
        }),
      })
    },
    retry(runId) {
      return requestJson<GenerationRun>(`${prefix}/runs/${runId}/retry`, {
        method: "POST",
      })
    },
  }
}

export const plantsPipelineApi = pipelineApi("/api/v1/admin/plant-pipeline")
export const discoveriesPipelineApi = pipelineApi("/api/v1/admin/discovery-pipeline")
