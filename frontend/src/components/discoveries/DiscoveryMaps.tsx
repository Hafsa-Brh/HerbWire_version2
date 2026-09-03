import { MapPin } from "lucide-react"
import { useCallback } from "react"
import type { ApiDiscoveryArticle, ApiDiscoveryGeography, ApiPublicDiscoveryArticle } from "../../api/discoveries"
import type { ApiDistributionRegion } from "../../api/plants"
import { useAsyncResource } from "../../hooks/useAsyncResource"
import { BotanicalDistributionMap } from "../plants/PlantPrimitives"

type DiscoveryWithMaps = ApiDiscoveryArticle | ApiPublicDiscoveryArticle

export function DiscoveryBotanicalDistribution({ article }: { article: DiscoveryWithMaps }) {
  const linkedPlant = article.linked_plants?.[0]
  const standalone = article.geography?.filter((item) => item.geography_kind === "botanical_distribution") ?? []
  const distribution: ApiDistributionRegion[] = linkedPlant?.distribution?.length ? linkedPlant.distribution : standalone.map((item, index) => ({
    code: `${item.source_id}-${index}`,
    name: item.display_label,
    level: 0,
    status: item.evidence_type.startsWith("introduced") ? "introduced" : item.evidence_type.includes("uncertain") ? "unknown" : "native",
    map_countries: [item.iso_country_code, ...(item.iso_country_codes ?? [])].filter(Boolean) as string[],
  }))
  if (!distribution.some((item) => item.map_countries?.length)) return null
  const name = linkedPlant?.common_name ?? article.botanical_identity?.common_name ?? "Medicinal plant"
  const summary = linkedPlant?.distribution_summary || standalone.map((item) => item.display_label).join("; ")
  const source = linkedPlant?.distribution_sources?.[0] ?? article.sources.find((item) => standalone.some((entry) => entry.source_id === item.external_identifier))
  const tone = { native: "bg-leaf", introduced: "bg-gold", unknown: "bg-muted" }
  return <section className="my-8 border-y border-line py-7" aria-label="Botanical distribution"><p className="hw-eyebrow inline-flex items-center gap-2"><MapPin size={14} /> Botanical distribution</p><h3 className="mt-3 font-serif text-3xl font-semibold tracking-[-.04em]">Where this medicinal plant occurs</h3>{summary ? <p className="mt-4 font-serif text-lg leading-relaxed text-muted">{summary}</p> : null}<BotanicalDistributionMap name={name} distribution={distribution} sourceUrl={source?.canonical_url} sourceLabel={source?.title} /><ul aria-label="Botanical distribution text summary" className="mt-5 grid gap-3 sm:grid-cols-2">{distribution.map((item) => <li key={item.code} className="flex gap-3 border border-line bg-sage/10 p-4"><span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${tone[item.status]}`} /><div><p className="font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">{item.status}</p><p className="mt-1 font-serif text-base leading-relaxed text-muted">{item.name}</p></div></li>)}</ul></section>
}

export function DiscoveryResearchGeography({ article }: { article: DiscoveryWithMaps }) {
  const items = article.geography?.filter((item) => item.geography_kind === "research_geography") ?? []
  if (!items.length) return null
  return <section className="my-8 border-y border-line py-7" aria-label="Research geography"><p className="hw-eyebrow inline-flex items-center gap-2"><MapPin size={14} /> Research geography</p><h3 className="mt-3 font-serif text-3xl font-semibold tracking-[-.04em]">{items[0].map_title}</h3>{items.some((item) => item.iso_country_code || item.iso_country_codes?.length) ? <ResearchMap items={items} /> : null}<ul className="mt-5 grid gap-3">{items.map((item) => <li key={`${item.source_id}-${item.evidence_type}-${item.display_label}`} className="border-l-2 border-gold pl-4"><p className="font-serif text-lg font-semibold">{item.display_label}</p><p className="mt-1 font-sans text-xs leading-relaxed text-muted">{item.evidence_type.replaceAll("_", " ")} / {item.qualification} Evidence: {item.supporting_text_location}.</p></li>)}</ul></section>
}

function ResearchMap({ items }: { items: ApiDiscoveryGeography[] }) {
  type WorldMap = { viewBox: string; locations: Array<{ id: string; name: string; path: string }> }
  const map = useAsyncResource<WorldMap>(useCallback(async () => { const module = await import("@svg-maps/world"); const value = module.default as WorldMap | { default: WorldMap }; return "default" in value ? value.default : value }, []))
  const codes = new Set(items.flatMap((item) => [item.iso_country_code, ...(item.iso_country_codes ?? [])].filter(Boolean).map((code) => code!.toUpperCase())))
  if (map.isLoading) return <div aria-label="Loading research map" className="mt-6 aspect-[1010/666] animate-pulse bg-sage/20" />
  if (map.error || !map.data) return <p className="mt-4 font-sans text-xs text-muted">The basemap is unavailable; the sourced research-geography text remains available below.</p>
  return <figure className="mt-6"><svg viewBox={map.data.viewBox} role="img" aria-label={items[0].map_title} className="h-auto w-full">{map.data.locations.map((location) => <path key={location.id} d={location.path} className={codes.has(location.id.toUpperCase()) ? "fill-leaf stroke-paper" : "fill-sage/40 stroke-paper"}><title>{location.name}</title></path>)}</svg><div aria-label="Research geography legend" className="mt-3 flex gap-4 border-t border-line pt-3 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-muted"><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-leaf" />Source-supported geography</span><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-sage" />Not specified</span></div><figcaption className="mt-2 font-sans text-[10px] text-muted">Highlighted only where the cited source supports the displayed evidence type. Affiliation is never presented as a study site. Basemap: SVG Maps World, CC BY 4.0.</figcaption></figure>
}
