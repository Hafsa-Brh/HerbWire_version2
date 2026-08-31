import { ArrowUpRight } from "lucide-react"
import { Link } from "react-router-dom"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"

export function DiscoveriesPage() {
  return (
    <SiteShell>
      <main id="top">
        <section className="hw-container border-b border-line py-10 md:py-16">
          <p className="hw-eyebrow">New Discoveries</p>
          <h1 className="mt-3 font-serif text-[clamp(3rem,8vw,7.5rem)] font-semibold leading-[.86] tracking-[-.075em] text-deep">New Discoveries</h1>
          <p className="mt-7 max-w-2xl font-serif text-xl leading-relaxed text-muted md:text-2xl">Reviewed discovery briefs will appear here after collection, source review, safety checks, and explicit human publication.</p>
        </section>
        <RouteState eyebrow="HerbWire / discoveries" title="No discoveries have been published yet." description="HerbWire's discovery collection pipeline is being prepared. Reviewed discoveries will appear here when the editorial workflow has approved them; no sample discoveries are shown as live content." primaryAction={{ label: "Browse plants", to: "/plants" }} secondaryAction={{ label: "Return home", to: "/" }} />
        <section className="hw-container border-b border-line py-14 md:py-20">
          <div className="max-w-2xl"><p className="hw-eyebrow">Coming later</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">Discovery briefs will stay source-led.</h2><p className="mt-5 font-serif text-lg leading-relaxed text-muted">Future entries will preserve original source provenance, translation context when needed, evidence limits, and safety notes.</p><Link to="/plants" className="mt-6 inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link">Read published plant profiles <ArrowUpRight size={14} /></Link></div>
        </section>
      </main>
      <Footer />
    </SiteShell>
  )
}
