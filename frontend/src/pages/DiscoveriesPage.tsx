import { ArrowUpRight } from "lucide-react"
import { useCallback } from "react"
import { Link } from "react-router-dom"
import { fetchPublishedDiscoveries } from "../api/discoveries"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

export function DiscoveriesPage() {
  const discoveries = useAsyncResource(
    useCallback((signal: AbortSignal) => fetchPublishedDiscoveries(signal), []),
  )
  return (
    <SiteShell>
      <main id="top">
        <section className="hw-container border-b border-line py-10 md:py-16">
          <p className="hw-eyebrow">Research, carefully translated</p>
          <h1 className="mt-3 max-w-5xl font-serif text-[clamp(3rem,8vw,7.5rem)] font-semibold leading-[.86] tracking-[-.075em] text-deep">New Discoveries</h1>
          <p className="mt-7 max-w-2xl font-serif text-xl leading-relaxed text-muted md:text-2xl">Evidence-qualified reports linking current research to HerbWire’s reviewed botanical encyclopedia.</p>
        </section>
        {discoveries.isLoading ? <RouteState eyebrow="HerbWire / discoveries" title="Loading published discoveries" description="Checking the canonical public archive." primaryAction={{ label: "Browse plants", to: "/plants" }} /> : null}
        {discoveries.error ? <RouteState eyebrow="HerbWire / discoveries" title="Discoveries are temporarily unavailable." description="The public discovery archive could not be loaded." primaryAction={{ label: "Try again", onClick: discoveries.reload }} secondaryAction={{ label: "Browse plants", to: "/plants" }} /> : null}
        {discoveries.data && discoveries.data.items.length === 0 ? <RouteState eyebrow="HerbWire / discoveries" title="No discoveries have been published yet." description="Review-ready, held, rejected, and approved drafts remain private until an editor completes a separate publication step." primaryAction={{ label: "Browse plants", to: "/plants" }} secondaryAction={{ label: "Return home", to: "/" }} /> : null}
        {discoveries.data?.items.length ? (
          <section className="hw-container grid gap-x-7 gap-y-12 border-b border-line py-12 sm:grid-cols-2 lg:grid-cols-3">
            {discoveries.data.items.map((article) => {
              const linkedPlant = article.linked_plants?.[0]
              const plant = linkedPlant ?? (article.botanical_identity ? {
                common_name: article.botanical_identity.common_name,
                scientific_name: article.botanical_identity.accepted_scientific_name,
              } : undefined)
              const place = article.geography?.find((item) => item.geography_kind === "research_geography")?.display_label
              return <article key={article.id} className="group">
                <Link to={`/discoveries/${article.slug}`} className="block">
                  <div className="aspect-[16/9] overflow-hidden rounded-2xl bg-sage/20">
                    {article.hero_image?.local_path ? <img src={article.hero_image?.local_path} alt={article.hero_image?.alt_text || `${plant?.common_name ?? "Medicinal plant"} botanical reference`} className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]" /> : null}
                  </div>
                  <div className="pt-5">
                    <p className="hw-eyebrow">{article.article_type ?? article.category}</p>
                    <h2 className="mt-3 font-serif text-3xl font-semibold leading-tight tracking-[-.04em] text-deep transition group-hover:text-leaf">{article.headline}</h2>
                    <p className="mt-3 font-sans text-sm leading-relaxed text-muted">{article.standfirst}</p>
                    <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 font-sans text-[10px] font-bold uppercase tracking-[.11em] text-muted">
                      {plant ? <span>{plant.common_name}</span> : null}
                      {article.evidence_strength ? <span>{article.evidence_strength} evidence</span> : null}
                      {place ? <span>{place}</span> : null}
                      <span>Source {new Date(article.sources[0]?.publication_date ?? article.published_at).toLocaleDateString()}</span>
                    </div>
                    <span className="mt-4 inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf">Read discovery <ArrowUpRight size={14} /></span>
                  </div>
                </Link>
              </article>
            })}
          </section>
        ) : null}
        <section className="hw-container py-14 md:py-20"><p className="hw-eyebrow">Editorial standard</p><h2 className="mt-2 max-w-2xl font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">A study report is not a prescription.</h2><p className="mt-5 max-w-2xl font-serif text-lg leading-relaxed text-muted">Each report preserves source provenance, design limits, safety context, and what the evidence cannot establish. Botanical images are references, never depictions of the reported study.</p></section>
      </main>
      <Footer />
    </SiteShell>
  )
}
