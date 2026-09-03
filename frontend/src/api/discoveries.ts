import { requestJson } from "./plants"
import type { ApiDistributionRegion } from "./plants"

export type ApiDiscoverySource = {
  id: string
  provider: string
  support_role: string
  external_identifier: string
  pmid: string | null
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
  distribution: ApiDistributionRegion[]
  distribution_summary: string
  distribution_sources: ApiDiscoverySource[]
}

export type ApiDiscoveryGeography = {
  country_or_region: string
  iso_country_code: string | null
  iso_country_codes?: string[]
  geography_kind: "botanical_distribution" | "research_geography"
  evidence_type: string
  source_id: string
  supporting_text_location: string
  confidence: string
  qualification: string
  display_label: string
  map_title: string
}

export type ApiBotanicalIdentity = {
  common_name: string
  accepted_scientific_name: string
  cited_scientific_name?: string | null
  family: string
  authority_source_id: string
  authority_taxon_id: string
  authority_url: string
  accepted: boolean
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
  botanical_identity: ApiBotanicalIdentity | null
  category: string
  relevance_reasons: string[]
  detected_entities: Array<{ label?: string; common_name?: string; scientific_name?: string | null; ambiguous?: boolean }>
  evidence_package: { evidence_type?: string; batch_id?: string; excerpts?: Array<{ text?: string; location?: string }> }
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

export type ApiDiscoveryFilterOption = { value: string; label: string }
export type ApiPublicDiscoveryFilters = {
  plants: ApiDiscoveryFilterOption[]
  study_types: ApiDiscoveryFilterOption[]
  evidence_strengths: ApiDiscoveryFilterOption[]
  publication_years: ApiDiscoveryFilterOption[]
  research_countries: ApiDiscoveryFilterOption[]
}
export type ApiPublicDiscoveryPage = { items: ApiPublicDiscoveryArticle[]; total: number; page: number; page_size: number; pages: number; total_pages: number; filters: ApiPublicDiscoveryFilters }
export type ApiDiscoveryPage = { items: ApiDiscoveryArticle[]; total: number; page: number; page_size: number; pages: number; total_pages: number }

export type DiscoveryArchiveQuery = {
  query?: string
  plant?: string
  studyType?: string
  evidenceStrength?: string
  publicationYear?: string
  researchCountry?: string
  page?: number
}

export function fetchPublishedDiscoveries(query: DiscoveryArchiveQuery = {}, signal?: AbortSignal): Promise<ApiPublicDiscoveryPage> {
  const params = new URLSearchParams({ page: String(query.page ?? 1), page_size: "12" })
  if (query.query?.trim()) params.set("query", query.query.trim())
  if (query.plant) params.set("plant", query.plant)
  if (query.studyType) params.set("study_type", query.studyType)
  if (query.evidenceStrength) params.set("evidence_strength", query.evidenceStrength)
  if (query.publicationYear) params.set("publication_year", query.publicationYear)
  if (query.researchCountry) params.set("research_country", query.researchCountry)
  return requestJson<ApiPublicDiscoveryPage>(`/api/v1/discoveries?${params}`, { signal })
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
