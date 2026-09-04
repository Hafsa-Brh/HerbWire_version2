import { requestJson } from "./plants"

export type AdminContentSummary = {
  total_content: number
  published_plants: number
  published_discoveries: number
  published_materials: number
  source_records: number
  provenance_relationships: number
  needs_review: number
}

export type AdminContentItem = {
  id: string
  title: string
  content_type: "plant_profile" | "discovery" | "material_story"
  content_type_label: string
  status: string
  timestamp: string
  plant_identity: string
  source_count: number
  origin: string
  public_path: string
  editorial_path: string
  pmid: string | null
}

export type AdminContentPage = {
  summary: AdminContentSummary
  items: AdminContentItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  statuses: string[]
}

export type AdminSourceAssociation = {
  content_id: string
  content_type: "plant_profile" | "discovery" | "material_story"
  title: string
  internal_path: string
}

export type AdminSourceItem = {
  id: string
  source_name: string
  source_type: string
  authoritative_domain: string
  external_identifier: string
  doi: string | null
  title: string
  publisher: string
  provenance_roles: string[]
  linked_content_count: number
  associated_content: AdminSourceAssociation[]
  created_at: string
  external_url: string
}

export type AdminSourcePage = {
  items: AdminSourceItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  source_count: number
  source_record_count: number
  source_types: string[]
}

type ContentQuery = { query?: string; contentType?: string; status?: string; page?: number }
type SourceQuery = { query?: string; sourceType?: string; contentType?: string; page?: number }

export function fetchAdminContent(options: ContentQuery, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(options.page ?? 1), page_size: "10" })
  if (options.query?.trim()) params.set("query", options.query.trim())
  if (options.contentType) params.set("content_type", options.contentType)
  if (options.status) params.set("editorial_status", options.status)
  return requestJson<AdminContentPage>(`/api/v1/admin/catalog/content?${params}`, { signal })
}

export function fetchAdminSources(options: SourceQuery, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(options.page ?? 1), page_size: "12" })
  if (options.query?.trim()) params.set("query", options.query.trim())
  if (options.sourceType) params.set("source_type", options.sourceType)
  if (options.contentType) params.set("content_type", options.contentType)
  return requestJson<AdminSourcePage>(`/api/v1/admin/catalog/sources?${params}`, { signal })
}
