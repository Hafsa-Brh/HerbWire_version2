export type ApiSourceRecord = {
  id: string
  external_identifier: string
  url: string
  canonical_url: string
  title: string
  publisher: string
  source_type: string
  original_language: string
  license_status: string
  supports: Record<string, boolean>
  accessed_at: string
}

export type ApiPlantMedia = {
  kind?: string
  source_page?: string
  original_url?: string
  local_path?: string
  file_title?: string
  creator?: string
  license?: string
  license_url?: string
  attribution?: string
  checksum_sha256?: string
  width?: number
  height?: number
  original_width?: number
  original_height?: number
  mime_type?: string
  alt_text?: string
  caption?: string
  downloaded_at?: string
  label?: string
  license_status?: string
}

export type ApiDistributionRegion = {
  code: string
  name: string
  status: "native" | "introduced" | "unknown"
  level: number
  map_countries?: string[]
}

export type ApiSafetyNote = {
  category: string
  statement: string
  route?: string
  source_ids?: string[]
}

export type ApiArticleDetails = {
  preparation_forms?: Array<{ label: string; plant_part: string; route: string; description: string; equivalence_warning: string; source_ids: string[] }>
  evidence_findings?: Array<{ heading: string; preparation: string; evidence_level: string; summary: string; limitations: string; source_ids: string[] }>
  mechanisms?: Array<{ preparation: string; summary: string; qualification: string; source_ids: string[] }>
  special_populations?: Array<{ population: string; guidance: string; source_ids: string[] }>
  interactions?: Array<{ interaction: string; evidence_level: string; statement: string; source_ids: string[] }>
  section_sources?: Record<string, string[]>
}

export type ApiPlantListItem = {
  id: string
  slug: string
  accepted_scientific_name: string
  botanical_author: string
  taxon_identifier: string
  known_synonyms: string[]
  display_common_name: string
  family_name: string | null
  diversity_tags: string[]
  summary: string
  status: string
  hero_image: ApiPlantMedia
  published_at: string | null
  source_count: number
  growth_form: string
  biome: string
  distribution_summary: string
  readiness_status: string
  version: number
}

export type ApiPlantPage = {
  items: ApiPlantListItem[]
  total: number
  page: number
  page_size: number
  pages: number
}

export type ApiPlantDetail = ApiPlantListItem & {
  introduction: string
  botanical_description: string
  traditional_uses: Array<{ tradition: string; statement: string; limitation: string; preparation?: string; evidence_class?: string; source_ids?: string[] }>
  parts_used: string[]
  distribution: ApiDistributionRegion[]
  preparation: string
  safety_notes: ApiSafetyNote[]
  evidence_notes: string
  article_details: ApiArticleDetails
  last_reviewed_at: string | null
  sources: ApiSourceRecord[]
}

export type PlantQuery = {
  query?: string
  family?: string
  tag?: string
  page?: number
  pageSize?: number
}

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
const LOOPBACK_HOSTNAMES = new Set(["localhost", "127.0.0.1", "[::1]"])

function alignPageLoopbackHostname(baseUrl: string): string {
  if (typeof window === "undefined" || !LOOPBACK_HOSTNAMES.has(window.location.hostname)) return baseUrl

  try {
    const apiUrl = new URL(baseUrl)
    if (LOOPBACK_HOSTNAMES.has(apiUrl.hostname)) apiUrl.hostname = window.location.hostname
    return apiUrl.toString().replace(new RegExp("/$"), "")
  } catch {
    return baseUrl
  }
}

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_HERBWIRE_API_BASE_URL?.trim()
  const baseUrl = configured && configured.length > 0 ? configured : DEFAULT_API_BASE_URL
  return alignPageLoopbackHostname(baseUrl.replace(new RegExp("/$"), ""))
}

export class ApiRequestError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = "ApiRequestError"
    this.status = status
    this.code = code
  }
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(getApiBaseUrl() + path, {
    ...init,
    credentials: init?.credentials ?? "include",
    headers: { Accept: "application/json", ...init?.headers },
  })

  if (!response.ok) {
    let code = "api_error"
    let message = "The request could not be completed."
    try {
      const body = await response.json() as { detail?: string | { code?: string; message?: string } }
      if (typeof body.detail === "string") message = body.detail
      else if (body.detail) {
        code = body.detail.code ?? code
        message = body.detail.message ?? message
      }
    } catch {
      // Keep the safe fallback when the server does not return JSON.
    }
    throw new ApiRequestError(response.status, code, message)
  }
  return (await response.json()) as T
}

export function fetchPlantPage(options: PlantQuery = {}, signal?: AbortSignal): Promise<ApiPlantPage> {
  const params = new URLSearchParams()
  if (options.query?.trim()) params.set("query", options.query.trim())
  if (options.family?.trim()) params.set("family", options.family.trim())
  if (options.tag?.trim()) params.set("tag", options.tag.trim())
  params.set("page", String(options.page ?? 1))
  params.set("page_size", String(options.pageSize ?? 12))
  return requestJson<ApiPlantPage>("/api/v1/plants?" + params.toString(), { signal })
}

export async function fetchPlants(query?: string, signal?: AbortSignal): Promise<ApiPlantListItem[]> {
  const page = await fetchPlantPage({ query, pageSize: 50 }, signal)
  return page.items
}

export function fetchPlant(slug: string, signal?: AbortSignal): Promise<ApiPlantDetail> {
  return requestJson<ApiPlantDetail>("/api/v1/plants/" + slug, { signal })
}
