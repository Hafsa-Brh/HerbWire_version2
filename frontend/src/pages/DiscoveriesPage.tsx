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
          <p className="hw-eyebrow">New Discoveries</p>
          <h1 className="mt-3 font-serif text-[clamp(3rem,8vw,7.5rem)] font-semibold leading-[.86] tracking-[-.075em] text-deep">New Discoveries</h1>
          <p className="mt-7 max-w-2xl font-serif text-xl leading-relaxed text-muted md:text-2xl">Reviewed discovery briefs appear here only after source review, safety checks, and a separate publication step.</p>
        </section>
        {discoveries.isLoading ? (
          <RouteState eyebrow="HerbWire / discoveries" title="Loading published discoveries" description="Checking the canonical public archive." primaryAction={{ label: "Browse plants", to: "/plants" }} />
        ) : null}
        {discoveries.error ? (
          <RouteState eyebrow="HerbWire / discoveries" title="Discoveries are temporarily unavailable." description="The public discovery archive could not be loaded." primaryAction={{ label: "Try again", onClick: discoveries.reload }} secondaryAction={{ label: "Browse plants", to: "/plants" }} />
        ) : null}
        {discoveries.data && discoveries.data.items.length === 0 ? (
          <RouteState eyebrow="HerbWire / discoveries" title="No discoveries have been published yet." description="Review-ready, held, rejected, and approved drafts remain private. Only a future explicit publisher action can make a discovery visible here." primaryAction={{ label: "Browse plants", to: "/plants" }} secondaryAction={{ label: "Return home", to: "/" }} />
        ) : null}
        {discoveries.data?.items.length ? (
          <section className="hw-container grid gap-5 border-b border-line py-12 md:grid-cols-2">
            {discoveries.data.items.map((article) => (
              <article key={article.id} className="border border-line bg-paper p-6">
                <p className="hw-eyebrow">{article.category}</p>
                <h2 className="mt-3 font-serif text-3xl font-semibold text-deep">{article.headline}</h2>
                <p className="mt-4 font-sans text-sm leading-relaxed text-muted">{article.standfirst}</p>
                <div className="mt-5 border-t border-line pt-4">
                  {article.sources.map((source) => (
                    <a key={source.id} href={source.canonical_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 font-sans text-xs font-bold text-leaf">
                      View PubMed source <ArrowUpRight size={14} />
                    </a>
                  ))}
                </div>
              </article>
            ))}
          </section>
        ) : null}
        <section className="hw-container border-b border-line py-14 md:py-20">
          <div className="max-w-2xl">
            <p className="hw-eyebrow">Editorial standard</p>
            <h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">Discovery briefs stay source-led.</h2>
            <p className="mt-5 font-serif text-lg leading-relaxed text-muted">Entries preserve original source provenance, evidence limits, and safety context. Research indexing is never presented as treatment advice.</p>
            <Link to="/plants" className="mt-6 inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link">Read published plant profiles <ArrowUpRight size={14} /></Link>
          </div>
        </section>
      </main>
      <Footer />
    </SiteShell>
  )
}