export type ApiHealthResponse = {
  status: "ok" | "degraded"
  service: string
  version: string
  database: "connected" | "disconnected"
}

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_HERBWIRE_API_BASE_URL?.trim()
  const baseUrl = configured && configured.length > 0 ? configured : DEFAULT_API_BASE_URL
  return baseUrl.replace(/\/$/, "")
}

export async function fetchHealth(): Promise<ApiHealthResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/health`, {
    headers: {
      Accept: "application/json",
    },
  })

  if (response.status !== 200 && response.status !== 503) {
    throw new Error("backend-unavailable")
  }

  return (await response.json()) as ApiHealthResponse
}
