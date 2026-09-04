import { requestJson } from "./plants"

export type MaterialMedia = { local_path: string; source_page: string; direct_asset_url: string; creator: string; title: string; attribution: string; license: string; license_url: string; checksum_sha256: string; alt_text: string }
export type MaterialSource = { id: string; source_name: string; title: string; source_type: string; external_identifier: string; canonical_url: string; supported_sections: string[] }
export type MaterialSummary = { id: string; slug: string; title: string; deck: string; category: string; material_labels: string[]; geography_label: string | null; reading_time_minutes: number; featured: boolean; published_at: string; hero_media: MaterialMedia }
export type MaterialDetail = MaterialSummary & { content_version: number; sections: Array<{key:string;heading:string;text:string;source_ids:string[]}>; sources: MaterialSource[]; related: MaterialSummary[] }
export type MaterialPage = { items: MaterialSummary[]; total: number; page: number; page_size: number; total_pages: number; categories: string[] }

export function fetchMaterials(category = "", signal?: AbortSignal) {
  const params = new URLSearchParams({ page_size: "12" })
  if (category) params.set("category", category)
  return requestJson<MaterialPage>(`/api/v1/materials?${params}`, { signal })
}
export function fetchMaterial(slug: string, signal?: AbortSignal) {
  return requestJson<MaterialDetail>(`/api/v1/materials/${encodeURIComponent(slug)}`, { signal })
}
