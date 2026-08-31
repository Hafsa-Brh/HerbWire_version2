import { Search, X } from "lucide-react"
import type { FormEvent } from "react"
import { useCallback, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { fetchPlants } from "../api/plants"
import { PlantCard } from "../components/plants/PlantPrimitives"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

export function PlantsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeQuery = searchParams.get("q") ?? ""
  const [draft, setDraft] = useState(activeQuery)
  const plants = useAsyncResource(useCallback((signal: AbortSignal) => fetchPlants(activeQuery, signal), [activeQuery]))
  const resultLabel = useMemo(() => activeQuery ? `${plants.data?.length ?? 0} result${plants.data?.length === 1 ? "" : "s"} for "${activeQuery}"` : "Published profiles", [activeQuery, plants.data])

  function submit(event: FormEvent) {
    event.preventDefault()
    const next = draft.trim()
    setSearchParams(next ? { q: next } : {})
  }

  return (
    <SiteShell>
      <main id="top">
        <section className="hw-container border-b border-line py-10 md:py-16">
          <div className="max-w-4xl">
            <p className="hw-eyebrow">Plant encyclopedia</p>
            <h1 className="mt-3 font-serif text-[clamp(3rem,8vw,7.5rem)] font-semibold leading-[.86] tracking-[-.075em] text-deep">Medicinal plant profiles</h1>
            <p className="mt-7 max-w-2xl font-serif text-xl leading-relaxed text-muted md:text-2xl">Only published, human-reviewed plant records appear in the public encyclopedia. Drafts remain private until explicit publication.</p>
          </div>
          <form onSubmit={submit} className="mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row" role="search">
            <div className="flex min-h-11 flex-1 items-center border border-line bg-paper px-4 focus-within:border-leaf">
              <Search size={18} className="mr-3 shrink-0 text-forest" />
              <input aria-label="Search plant profiles" value={draft} onChange={(event) => setDraft(event.target.value)} className="min-w-0 flex-1 bg-transparent font-sans text-sm text-deep outline-none placeholder:text-muted/75" placeholder="Search by common or scientific name" />
              {draft ? <button type="button" onClick={() => setDraft("")} aria-label="Clear search" className="ml-3 text-muted transition hover:text-leaf"><X size={18} /></button> : null}
            </div>
            <button type="submit" className="min-h-11 bg-forest px-5 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream transition hover:bg-leaf">Search</button>
          </form>
        </section>
        {plants.isLoading ? <RouteState eyebrow="HerbWire / loading" title="Loading plant profiles." description="The public API is retrieving published profiles from PostgreSQL." primaryAction={{ label: "Return home", to: "/" }} /> : null}
        {plants.error ? <RouteState eyebrow="HerbWire / interrupted" title="The encyclopedia API is unavailable." description="Published plant profiles could not be loaded from FastAPI." primaryAction={{ label: "Try again", onClick: plants.reload }} secondaryAction={{ label: "Return home", to: "/" }} /> : null}
        {plants.data && !plants.isLoading && !plants.error ? (
          <section className="hw-container py-14 md:py-20">
            <div className="flex items-end justify-between border-b-2 border-forest pb-4">
              <div><p className="hw-eyebrow">The archive</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">{resultLabel}</h2></div>
              <span className="hidden font-serif text-sm italic text-muted sm:block">{plants.data.length} visible</span>
            </div>
            {plants.data.length ? <div className="grid gap-6 pt-8 sm:grid-cols-2 md:grid-cols-3 md:gap-8">{plants.data.map((plant) => <PlantCard key={plant.id} plant={plant} />)}</div> : <p className="max-w-2xl pt-8 font-serif text-xl leading-relaxed text-muted">No published profiles match that search. Unpublished drafts are intentionally absent from the public API.</p>}
          </section>
        ) : null}
      </main>
      <Footer />
    </SiteShell>
  )
}
