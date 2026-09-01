import { ChevronLeft, ChevronRight, Filter, Search, X } from "lucide-react"
import type { FormEvent } from "react"
import { useCallback, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { fetchPlantPage } from "../api/plants"
import { PlantCard } from "../components/plants/PlantPrimitives"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

export function PlantsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeQuery = searchParams.get("q") ?? ""
  const activeFamily = searchParams.get("family") ?? ""
  const activeTag = searchParams.get("tag") ?? ""
  const activePage = Math.max(1, Number(searchParams.get("page") ?? "1") || 1)
  const [draft, setDraft] = useState(activeQuery)
  const [family, setFamily] = useState(activeFamily)
  const [tag, setTag] = useState(activeTag)
  const plants = useAsyncResource(useCallback(
    (signal: AbortSignal) => fetchPlantPage({ query: activeQuery, family: activeFamily, tag: activeTag, page: activePage }, signal),
    [activeFamily, activePage, activeQuery, activeTag],
  ))
  const resultLabel = useMemo(() => {
    if (activeQuery) return (plants.data?.total ?? 0) + " result" + (plants.data?.total === 1 ? "" : "s") + ' for "' + activeQuery + '"'
    return "MEDICINAL PLANTS"
  }, [activeQuery, plants.data?.total])

  function updateParams(values: { q?: string; family?: string; tag?: string; page?: number }) {
    const next = new URLSearchParams()
    if (values.q?.trim()) next.set("q", values.q.trim())
    if (values.family?.trim()) next.set("family", values.family.trim())
    if (values.tag?.trim()) next.set("tag", values.tag.trim())
    if ((values.page ?? 1) > 1) next.set("page", String(values.page))
    setSearchParams(next)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    updateParams({ q: draft, family, tag, page: 1 })
  }

  function clearFilters() {
    setDraft("")
    setFamily("")
    setTag("")
    setSearchParams({})
  }

  return (
    <SiteShell>
      <main id="top">
        {plants.isLoading ? <RouteState eyebrow="HerbWire / loading" title="Loading plant profiles." description="The public API is retrieving published profiles from PostgreSQL." primaryAction={{ label: "Return home", to: "/" }} /> : null}
        {plants.error ? <RouteState eyebrow="HerbWire / interrupted" title="The encyclopedia API is unavailable." description="Published plant profiles could not be loaded from FastAPI." primaryAction={{ label: "Try again", onClick: plants.reload }} secondaryAction={{ label: "Return home", to: "/" }} /> : null}
        {plants.data && !plants.isLoading && !plants.error ? (
          <section className="hw-container py-14 md:py-20">
            <div className="flex items-end justify-between border-b-2 border-forest pb-4">
              <div><p className="hw-eyebrow">The archive</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">{resultLabel}</h2></div>
              <span className="hidden font-serif text-sm italic text-muted sm:block">{plants.data.total} published</span>
            </div>
            <form onSubmit={submit} className="mt-6 grid gap-3 md:grid-cols-[2fr_1fr_1fr_auto]" role="search">
              <label className="flex min-h-11 items-center border border-line bg-paper px-4 focus-within:border-leaf">
                <Search size={18} className="mr-3 shrink-0 text-forest" />
                <span className="sr-only">Search plant profiles</span>
                <input aria-label="Search plant profiles" value={draft} onChange={(event) => setDraft(event.target.value)} className="min-w-0 flex-1 bg-transparent font-sans text-sm text-deep outline-none placeholder:text-muted/75" placeholder="Common or scientific name" />
              </label>
              <label className="flex min-h-11 items-center border border-line bg-paper px-3 focus-within:border-leaf">
                <Filter size={15} className="mr-2 text-forest" />
                <span className="sr-only">Filter by family</span>
                <input aria-label="Filter by family" value={family} onChange={(event) => setFamily(event.target.value)} className="min-w-0 w-full bg-transparent font-sans text-sm text-deep outline-none placeholder:text-muted/75" placeholder="Family" />
              </label>
              <label className="flex min-h-11 items-center border border-line bg-paper px-3 focus-within:border-leaf">
                <span className="sr-only">Filter by region or tradition</span>
                <input aria-label="Filter by region or tradition" value={tag} onChange={(event) => setTag(event.target.value)} className="min-w-0 w-full bg-transparent font-sans text-sm text-deep outline-none placeholder:text-muted/75" placeholder="Region / tradition" />
              </label>
              <button type="submit" className="min-h-11 bg-forest px-5 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream transition hover:bg-leaf">Search</button>
              {draft || family || tag ? <button type="button" onClick={clearFilters} className="inline-flex min-h-9 items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-muted hover:text-leaf md:col-span-4 md:justify-self-start"><X size={15} /> Clear filters</button> : null}
            </form>
            {plants.data.items.length ? <div className="grid gap-6 pt-8 sm:grid-cols-2 md:grid-cols-3 md:gap-8">{plants.data.items.map((plant) => <PlantCard key={plant.id} plant={plant} />)}</div> : <p className="max-w-2xl pt-8 font-serif text-xl leading-relaxed text-muted">No published profiles match those filters. Unpublished drafts are intentionally absent from the public API.</p>}
            {plants.data.pages > 1 ? <nav aria-label="Plant pages" className="mt-12 flex items-center justify-between border-t border-line pt-5">
              <button type="button" disabled={activePage <= 1} onClick={() => updateParams({ q: activeQuery, family: activeFamily, tag: activeTag, page: activePage - 1 })} className="inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest disabled:opacity-30"><ChevronLeft size={16} /> Previous</button>
              <span className="font-sans text-xs text-muted">Page {plants.data.page} of {plants.data.pages}</span>
              <button type="button" disabled={activePage >= plants.data.pages} onClick={() => updateParams({ q: activeQuery, family: activeFamily, tag: activeTag, page: activePage + 1 })} className="inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest disabled:opacity-30">Next <ChevronRight size={16} /></button>
            </nav> : null}
          </section>
        ) : null}
      </main>
      <Footer />
    </SiteShell>
  )
}
