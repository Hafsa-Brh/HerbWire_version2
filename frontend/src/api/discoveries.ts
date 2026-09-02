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

export type ApiDiscoveryPlant = {
  id: string
  slug: string
  common_name: string
  scientific_name: string
}

export type ApiDiscoveryGeography = {
  country_or_region: string
  iso_country_code: string | null
  evidence_type: string
  source_id: string
  supporting_text_location: string
  confidence: string
  qualification: string
  display_label: string
  map_title: string
}

export type ApiDiscoveryArticle = {
  id: string
  slug: string
  status: string
  headline: string
  standfirst: string
  body_blocks: Array<{ key?: string; heading?: string; text?: string; source_ids?: string[]; evidence_locations?: string[] }>
  limitations: string[]
  safety_context: string
  cannot_conclude: string[]
  qa_payload: { passed?: boolean; reason_codes?: string[]; checklist?: Record<string, boolean> }
  version: number
  content_origin: string
  article_type: string | null
  research_date: string | null
  research_question: string | null
  research_context: string | null
  study_design: string | null
  evidence_base: string | null
  intervention: string | null
  comparator: string | null
  main_findings: string[]
  evidence_strength: string | null
  evidence_strength_rationale: string | null
  why_matters: string | null
  practical_interpretation: string | null
  section_sources: Record<string, { source_ids: string[]; evidence_locations: string[] }>
  hero_image: Record<string, string>
  geography: ApiDiscoveryGeography[]
  linked_plants: ApiDiscoveryPlant[]
  category: string
  relevance_reasons: string[]
  detected_entities: Array<{ label?: string; common_name?: string; scientific_name?: string | null; ambiguous?: boolean }>
  evidence_package: { evidence_type?: string; excerpts?: Array<{ text?: string; location?: string }> }
  sources: ApiDiscoverySource[]
  review_id: string | null
  review_status: string | null
  reviewer_name: string | null
  decision_reason: string | null
  created_at: string
  reviewed_at: string | null
  published_at: string | null
}

export type ApiPublicDiscoveryArticle = Omit<ApiDiscoveryArticle,
  "status" | "content_origin" | "qa_payload" | "relevance_reasons" | "detected_entities" |
  "evidence_package" | "review_id" | "review_status" | "reviewer_name" | "decision_reason" |
  "reviewed_at"
> & { published_at: string }

export type ApiPublicDiscoveryPage = { items: ApiPublicDiscoveryArticle[]; total: number; page: number; page_size: number; pages: number }
export type ApiDiscoveryPage = { items: ApiDiscoveryArticle[]; total: number; page: number; page_size: number; pages: number }

export function fetchPublishedDiscoveries(signal?: AbortSignal): Promise<ApiPublicDiscoveryPage> {
  return requestJson<ApiPublicDiscoveryPage>("/api/v1/discoveries?page=1&page_size=12", { signal })
}

export function fetchPublishedDiscovery(slug: string, signal?: AbortSignal): Promise<ApiPublicDiscoveryArticle> {
  return requestJson<ApiPublicDiscoveryArticle>(`/api/v1/discoveries/${encodeURIComponent(slug)}`, { signal })
}

export function fetchDiscoveryReviews(signal?: AbortSignal): Promise<ApiDiscoveryPage> {
  return requestJson<ApiDiscoveryPage>("/api/v1/admin/discovery/reviews?page=1&page_size=50", { signal })
}

export function triggerPubMedRun(input: { start_date: string; end_date: string; max_records: number; date_type: "publication" | "indexing" }) {
  return requestJson("/api/v1/admin/discovery/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source: "pubmed", ...input }) })
}

export function decideDiscovery(articleId: string, decision: "approve" | "hold" | "reject" | "publish", reason?: string): Promise<ApiDiscoveryArticle> {
  return requestJson<ApiDiscoveryArticle>(`/api/v1/admin/discovery/reviews/${articleId}/${decision}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_name: "HerbWire editor", reason }),
  })
}