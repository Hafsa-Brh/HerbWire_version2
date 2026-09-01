import { ArrowUpRight } from "lucide-react"
import { useCallback } from "react"
import { Link } from "react-router-dom"
import type { ApiPlantDetail, ApiPlantListItem, ApiPlantMedia } from "../../api/plants"
import { useAsyncResource } from "../../hooks/useAsyncResource"
import loginMonsteraImage from "../../assets/login-monstera.png"

export function StatusPill({ children }: { children: string }) {
  const normalized = children.toLowerCase()
  const tone = normalized === "published" || normalized === "approved"
    ? "bg-sage/30 text-forest"
    : normalized.includes("review") || normalized.includes("held")
      ? "bg-gold/20 text-deep"
      : "bg-rust/15 text-rust"
  return <span className={"inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-sans text-[10px] font-bold uppercase tracking-[.08em] " + tone}><span className="h-1.5 w-1.5 rounded-full bg-current" />{children}</span>
}

export function BotanicalImage({ label, image, compact = false }: { label: string; image?: ApiPlantMedia; compact?: boolean }) {
  const source = image?.local_path || loginMonsteraImage
  const alt = image?.local_path ? image.alt_text || ("Botanical image of " + label) : ""
  return (
    <div className={"relative overflow-hidden rounded-xl bg-sage/30 " + (compact ? "aspect-[4/3]" : "aspect-[16/9]")} role={alt ? undefined : "img"} aria-label={alt ? undefined : "Botanical image unavailable for " + label}>
      <img
        className="hw-image h-full w-full object-cover"
        src={source}
        alt={alt}
        loading="lazy"
        onError={(event) => {
          event.currentTarget.src = loginMonsteraImage
          event.currentTarget.alt = ""
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-deep/35 via-transparent to-transparent" />
    </div>
  )
}

export function PlantDistributionMap({ plant }: { plant: ApiPlantDetail }) {
  type WorldMap = { viewBox: string; locations: Array<{ id: string; name: string; path: string }> }
  const countryStatuses = new Map<string, Set<string>>()
  plant.distribution.forEach((region) => region.map_countries?.forEach((country) => {
    const statuses = countryStatuses.get(country) ?? new Set<string>()
    statuses.add(region.status)
    countryStatuses.set(country, statuses)
  }))
  const map = useAsyncResource<WorldMap>(useCallback(async () => {
    const module = await import("@svg-maps/world")
    const candidate = module.default as WorldMap | { default: WorldMap }
    return "locations" in candidate ? candidate : candidate.default
  }, []))
  const distributionSource = plant.sources.find((source) => source.supports.distribution)
  const mapSource = plant.sources.find((source) => source.canonical_url.includes("gbif.org/dataset")) ?? distributionSource
  const fill = (country: string) => {
    const statuses = countryStatuses.get(country.toUpperCase())
    if (statuses?.has("native") && statuses.has("introduced")) return "fill-rust/70"
    if (statuses?.has("native")) return "fill-leaf/80"
    if (statuses?.has("introduced")) return "fill-gold/85"
    if (statuses?.has("unknown")) return "fill-muted/70"
    return "fill-sage/25"
  }
  const label = (country: string) => {
    const statuses = countryStatuses.get(country.toUpperCase())
    if (statuses?.has("native") && statuses.has("introduced")) return "native and introduced"
    return statuses ? Array.from(statuses).join(", ") : "not listed"
  }

  if (!countryStatuses.size) return null
  if (map.isLoading) return <div className="mt-7 aspect-[1010/666] animate-pulse border border-line bg-sage/20" aria-label="Loading distribution map" />
  if (map.error || !map.data) return <p className="mt-4 font-sans text-xs leading-relaxed text-muted">The country basemap could not be loaded; the sourced distribution lists remain available below.</p>

  return <figure className="mt-7 border border-line bg-sage/10 p-3 sm:p-5">
    <svg viewBox={map.data.viewBox} role="img" aria-label={`Country-level distribution overview for ${plant.display_common_name}`} className="h-auto w-full" preserveAspectRatio="xMidYMid meet">
      <title>Country-level distribution overview for {plant.display_common_name}</title>
      {map.data.locations.map((location) => <path key={location.id} id={`map-${location.id}`} d={location.path} className={`${fill(location.id)} stroke-paper stroke-[0.7] transition-colors`}><title>{location.name}: {label(location.id)}</title></path>)}
    </svg>
    <div aria-label="Map legend" className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-line pt-3 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-muted"><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-leaf" />Native</span><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-gold" />Introduced</span><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-rust" />Both statuses</span><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-muted" />Origin uncertain</span><span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-sage" />Not listed</span></div>
    <figcaption className="mt-3 font-sans text-[10px] leading-relaxed text-muted">Country-level overview aggregated from WCVP botanical regions; subnational WGSRPD regions are not implied to cover an entire country uniformly. Distribution: {mapSource ? <a href={mapSource.url} target="_blank" rel="noreferrer" className="font-bold text-leaf hover:text-forest">{mapSource.publisher}</a> : "profile provenance"}. Basemap: <a href="https://github.com/VictorCazanave/svg-maps/tree/master/packages/world" target="_blank" rel="noreferrer" className="font-bold text-leaf hover:text-forest">SVG Maps World</a>, CC BY 4.0.</figcaption>
  </figure>
}
export function PlantCard({ plant }: { plant: ApiPlantListItem }) {
  return (
    <article className="group">
      <Link to={"/plants/" + plant.slug} className="block">
        <div className="hw-image-wrap relative aspect-[4/3] overflow-hidden rounded-xl bg-sage/30">
          <BotanicalImage label={plant.display_common_name} image={plant.hero_image} compact />
          <div className="absolute left-3 top-3 bg-paper px-2 py-1"><StatusPill>{plant.status}</StatusPill></div>
        </div>
        <div className="pt-5">
          <p className="hw-eyebrow">{plant.family_name ?? "Family under review"}</p>
          <h3 className="mt-2 font-serif text-[1.45rem] font-semibold leading-[1.08] tracking-[-.025em] text-deep transition group-hover:text-leaf sm:text-[1.6rem]">{plant.display_common_name}</h3>
          <p className="mt-2 font-serif text-sm italic text-muted">{plant.accepted_scientific_name}</p>
          <p className="mt-3 font-serif text-[15px] leading-relaxed text-muted">{plant.summary}</p>
          <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 font-sans text-[11px] text-muted">
            <span>{plant.source_count} provenance sources</span><span aria-hidden="true">/</span><span className="inline-flex items-center gap-1 font-sans text-xs font-bold text-leaf">Read profile <ArrowUpRight size={14} /></span>
          </div>
        </div>
      </Link>
    </article>
  )
}
