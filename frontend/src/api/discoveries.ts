import { requestJson } from "./plants"

export type ApiDiscoverySource = {
  id: string
  pmid: string
  doi: string | null
  canonical_url: string
  title: string
  authors: string[]
  journal: string | null
  publication_date: string | null
}

export type ApiDiscoveryArticle = {
  id: string
  slug: string
  status: string
  headline: string
  standfirst: string
  body_blocks: Array<{ heading?: string; text?: string; source_record_ids?: string[] }>
  limitations: string[]
  safety_context: string
  cannot_conclude: string[]
  qa_payload: { passed?: boolean; reason_codes?: string[]; checklist?: Record<string, boolean> }
  version: number
  category: string
  relevance_reasons: string[]
  detected_entities: Array<{
    label?: string
    common_name?: string
    scientific_name?: string | null
    ambiguous?: boolean
  }>
  evidence_package: {
    evidence_type?: string
    excerpts?: Array<{ text?: string; location?: string }>
  }
  sources: ApiDiscoverySource[]
  review_id: string | null
  review_status: string | null
  reviewer_name: string | null
  decision_reason: string | null
  created_at: string
  reviewed_at: string | null
  published_at: string | null
}

export type ApiPublicDiscoveryArticle = Pick<ApiDiscoveryArticle,
  | "id" | "slug" | "headline" | "standfirst" | "body_blocks"
  | "limitations" | "safety_context" | "cannot_conclude" | "version"
  | "category" | "sources" | "created_at" | "published_at"
>

export type ApiPublicDiscoveryPage = {
  items: ApiPublicDiscoveryArticle[]
  total: number
  page: number
  page_size: number
  pages: number
}

export type ApiDiscoveryPage = {
  items: ApiDiscoveryArticle[]
  total: number
  page: number
  page_size: number
  pages: number
}

export function fetchPublishedDiscoveries(signal?: AbortSignal): Promise<ApiPublicDiscoveryPage> {
  return requestJson<ApiPublicDiscoveryPage>("/api/v1/discoveries?page=1&page_size=12", { signal })
}

export function fetchDiscoveryReviews(signal?: AbortSignal): Promise<ApiDiscoveryPage> {
  return requestJson<ApiDiscoveryPage>("/api/v1/admin/discovery/reviews?page=1&page_size=50", { signal })
}

export function triggerPubMedRun(input: {
  start_date: string
  end_date: string
  max_records: number
  date_type: "publication" | "indexing"
}) {
  return requestJson("/api/v1/admin/discovery/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source: "pubmed", ...input }),
  })
}

export function decideDiscovery(
  articleId: string,
  decision: "approve" | "hold" | "reject",
  reason?: string,
): Promise<ApiDiscoveryArticle> {
  return requestJson<ApiDiscoveryArticle>(
    `/api/v1/admin/discovery/reviews/${articleId}/${decision}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewer_name: "HerbWire editor", reason }),
    },
  )
}