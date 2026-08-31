export type ApiSourceRecord = {
  id: string
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

export type ApiPlantListItem = {
  id: string
  slug: string
  accepted_scientific_name: string
  display_common_name: string
  family_name: string | null
  summary: string
  status: string
  hero_image: {
    kind?: string
    label?: string
    license_status?: string
    attribution?: string
    alt_text?: string
  }
  published_at: string | null
  source_count: number
}

export type ApiPlantDetail = ApiPlantListItem & {
  introduction: string
  botanical_description: string
  traditional_uses: Array<{ tradition: string; statement: string; limitation: string }>
  parts_used: string[]
  distribution: string[]
  preparation: string
  safety_notes: string[]
  evidence_notes: string
  last_reviewed_at: string | null
  sources: ApiSourceRecord[]
}

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
const LOOPBACK_HOSTNAMES = new Set(["localhost", "127.0.0.1", "[::1]"])

function alignPageLoopbackHostname(baseUrl: string): string {
  if (typeof window === "undefined" || !LOOPBACK_HOSTNAMES.has(window.location.hostname)) return baseUrl

  try {
    const apiUrl = new URL(baseUrl)
    if (LOOPBACK_HOSTNAMES.has(apiUrl.hostname)) apiUrl.hostname = window.location.hostname
    return apiUrl.toString().replace(/\/$/, "")
  } catch {
    return baseUrl
  }
}

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_HERBWIRE_API_BASE_URL?.trim()
  const baseUrl = configured && configured.length > 0 ? configured : DEFAULT_API_BASE_URL
  return alignPageLoopbackHostname(baseUrl.replace(/\/$/, ""))
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    credentials: init?.credentials ?? "include",
    headers: { Accept: "application/json", ...init?.headers },
  })

  if (!response.ok) throw new Error(`api-${response.status}`)
  return (await response.json()) as T
}

export function fetchPlants(query?: string, signal?: AbortSignal): Promise<ApiPlantListItem[]> {
  const search = query?.trim()
  const suffix = search ? `?query=${encodeURIComponent(search)}` : ""
  return requestJson<ApiPlantListItem[]>(`/api/v1/plants${suffix}`, { signal })
}

export function fetchPlant(slug: string, signal?: AbortSignal): Promise<ApiPlantDetail> {
  return requestJson<ApiPlantDetail>(`/api/v1/plants/${slug}`, { signal })
}
