import { ArrowUpRight, ChevronLeft, ChevronRight, Search, X } from "lucide-react"
import type { FormEvent } from "react"
import { useCallback } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { fetchPublishedDiscoveries } from "../api/discoveries"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

type ArchiveValues = {
  query: string
  plant: string
  studyType: string
  evidenceStrength: string
  publicationYear: string
  researchCountry: string
}

export function DiscoveriesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeQuery = searchParams.get("q") ?? ""
  const activePlant = searchParams.get("plant") ?? ""
  const activeStudyType = searchParams.get("study_type") ?? ""
  const activeEvidenceStrength = searchParams.get("evidence_strength") ?? ""
  const activePublicationYear = searchParams.get("year") ?? ""
  const activeResearchCountry = searchParams.get("country") ?? ""
  const active: ArchiveValues = { query: activeQuery, plant: activePlant, studyType: activeStudyType, evidenceStrength: activeEvidenceStrength, publicationYear: activePublicationYear, researchCountry: activeResearchCountry }
  const requestedPage = Math.max(1, Number(searchParams.get("page") ?? "1") || 1)
  const discoveries = useAsyncResource(useCallback(
    (signal: AbortSignal) => fetchPublishedDiscoveries({ query: activeQuery, plant: activePlant, studyType: activeStudyType, evidenceStrength: activeEvidenceStrength, publicationYear: activePublicationYear, researchCountry: activeResearchCountry, page: requestedPage }, signal),
    [activeQuery, activePlant, activeStudyType, activeEvidenceStrength, activePublicationYear, activeResearchCountry, requestedPage],
  ))
  const hasFilters = Object.values(active).some(Boolean)

  function updateParams(values: ArchiveValues, page = 1) {
    const next = new URLSearchParams()
    if (values.query.trim()) next.set("q", values.query.trim())
    if (values.plant) next.set("plant", values.plant)
    if (values.studyType) next.set("study_type", values.studyType)
    if (values.evidenceStrength) next.set("evidence_strength", values.evidenceStrength)
    if (values.publicationYear) next.set("year", values.publicationYear)
    if (values.researchCountry) next.set("country", values.researchCountry)
    if (page > 1) next.set("page", String(page))
    setSearchParams(next)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    const form = new FormData(event.currentTarget as HTMLFormElement)
    updateParams({ query: String(form.get("query") ?? ""), plant: String(form.get("plant") ?? ""), studyType: String(form.get("study_type") ?? ""), evidenceStrength: String(form.get("evidence_strength") ?? ""), publicationYear: String(form.get("publication_year") ?? ""), researchCountry: String(form.get("research_country") ?? "") }, 1)
  }

  function clearFilters() {
    setSearchParams({})
  }

  const filters = discoveries.data?.filters
  return <SiteShell><main id="top">
    {discoveries.isLoading ? <RouteState eyebrow="HerbWire / discoveries" title="Loading published discoveries" description="Checking the canonical public archive." primaryAction={{ label: "Browse plants", to: "/plants" }} /> : null}
    {discoveries.error ? <RouteState eyebrow="HerbWire / discoveries" title="Discoveries are temporarily unavailable." description="The public discovery archive could not be loaded." primaryAction={{ label: "Try again", onClick: discoveries.reload }} secondaryAction={{ label: "Browse plants", to: "/plants" }} /> : null}
    {discoveries.data && !discoveries.isLoading && !discoveries.error ? <section className="hw-container py-14 md:py-20">
      <div className="flex items-end justify-between border-b-2 border-forest pb-4"><div><p className="hw-eyebrow">The research archive</p><h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">TRADITIONAL MEDICINE DISCOVERIES</h1></div><span className="hidden font-serif text-sm italic text-muted sm:block">{discoveries.data.total} published</span></div>
      <form key={searchParams.toString()} onSubmit={submit} role="search" className="mt-6 grid gap-3 lg:grid-cols-6">
        <label className="flex min-h-11 items-center border border-line bg-paper px-4 focus-within:border-leaf lg:col-span-2"><Search size={18} className="mr-3 shrink-0 text-forest" /><span className="sr-only">Search discoveries</span><input name="query" aria-label="Search discoveries" maxLength={120} defaultValue={active.query} className="min-w-0 flex-1 bg-transparent font-sans text-sm text-deep outline-none" placeholder="Headline, plant, journal or PMID" /></label>
        <FilterSelect name="plant" label="Filter by plant" value={active.plant} options={filters?.plants ?? []} placeholder="All plants" />
        <FilterSelect name="study_type" label="Filter by study type" value={active.studyType} options={filters?.study_types ?? []} placeholder="All study types" />
        <FilterSelect name="evidence_strength" label="Filter by evidence strength" value={active.evidenceStrength} options={filters?.evidence_strengths ?? []} placeholder="All evidence" />
        <button type="submit" className="min-h-11 bg-forest px-5 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream transition hover:bg-leaf">Search</button>
        <div className="grid gap-3 sm:grid-cols-2 lg:col-span-2"><FilterSelect name="publication_year" label="Filter by publication year" value={active.publicationYear} options={filters?.publication_years ?? []} placeholder="All years" /><FilterSelect name="research_country" label="Filter by research country" value={active.researchCountry} options={filters?.research_countries ?? []} placeholder="All research countries" /></div>
        {hasFilters ? <button type="button" onClick={clearFilters} className="inline-flex min-h-9 items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-muted hover:text-leaf lg:col-span-4 lg:justify-self-start"><X size={15} /> Clear all</button> : null}
      </form>
      {discoveries.data.items.length ? <div className="grid gap-x-7 gap-y-12 pt-10 sm:grid-cols-2 lg:grid-cols-3">{discoveries.data.items.map((article) => {
        const linkedPlant = article.linked_plants?.[0]
        const plant = linkedPlant ?? (article.botanical_identity ? { common_name: article.botanical_identity.common_name, scientific_name: article.botanical_identity.accepted_scientific_name } : undefined)
        const place = article.geography?.find((item) => item.geography_kind === "research_geography")?.display_label
        return <article key={article.id} className="group border-b border-line pb-8"><Link to={`/discoveries/${article.slug}`} className="block"><div className="relative aspect-[16/9] overflow-hidden rounded-2xl bg-sage/20">{article.hero_image?.local_path ? <img src={article.hero_image.local_path} alt={article.hero_image.alt_text || `${plant?.common_name ?? "Medicinal plant"} editorial cover`} className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]" /> : null}<span className="absolute left-3 top-3 bg-deep/90 px-3 py-1.5 font-sans text-[10px] font-bold uppercase tracking-[.12em] text-cream">{article.article_type ?? article.category}</span></div><div className="pt-5"><p className="font-serif text-sm text-muted">{plant?.common_name}{plant?.scientific_name ? <> / <i>{plant.scientific_name}</i></> : null}</p><h3 className="mt-3 font-serif text-3xl font-semibold leading-tight tracking-[-.04em] text-deep transition group-hover:text-leaf">{article.headline}</h3><p className="mt-3 font-sans text-sm leading-relaxed text-muted">{article.standfirst}</p><div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 font-sans text-[10px] font-bold uppercase tracking-[.11em] text-muted">{article.evidence_strength ? <span>{article.evidence_strength} evidence</span> : null}{place ? <span>{place}</span> : null}<span>{new Date(article.sources[0]?.publication_date ?? article.published_at).toLocaleDateString()}</span></div><span className="mt-4 inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf">Read discovery <ArrowUpRight size={14} /></span></div></Link></article>
      })}</div> : <RouteState eyebrow="HerbWire / discoveries" title={hasFilters ? "No discoveries match those filters." : "No discoveries have been published yet."} description={hasFilters ? "Clear one or more filters and search again." : "Review-ready, held, rejected, and approved drafts remain private until an editor completes a separate publication step."} primaryAction={hasFilters ? { label: "Clear filters", onClick: clearFilters } : { label: "Browse plants", to: "/plants" }} />}
      {discoveries.data.items.length ? <nav aria-label="Discovery archive pagination" className="mt-12 flex items-center justify-between border-t border-line pt-5"><button type="button" disabled={discoveries.data.page <= 1} onClick={() => updateParams(active, discoveries.data!.page - 1)} className="inline-flex items-center gap-2 border border-line px-4 py-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest disabled:opacity-35"><ChevronLeft size={15} /> Previous</button><span className="font-sans text-xs text-muted">Page {discoveries.data.page} of {discoveries.data.total_pages}</span><button type="button" disabled={discoveries.data.page >= discoveries.data.total_pages} onClick={() => updateParams(active, discoveries.data!.page + 1)} className="inline-flex items-center gap-2 border border-line px-4 py-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest disabled:opacity-35">Next <ChevronRight size={15} /></button></nav> : null}
    </section> : null}
  </main><Footer /></SiteShell>
}

function FilterSelect({ name, label, value, options, placeholder }: { name: string; label: string; value: string; options: Array<{ value: string; label: string }>; placeholder: string }) {
  return <label className="flex min-h-11 items-center border border-line bg-paper px-3 focus-within:border-leaf"><span className="sr-only">{label}</span><select name={name} aria-label={label} defaultValue={value} className="min-w-0 w-full bg-transparent font-sans text-sm text-deep outline-none"><option value="">{placeholder}</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
}
