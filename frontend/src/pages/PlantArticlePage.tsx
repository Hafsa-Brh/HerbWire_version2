import { ArrowLeft, ExternalLink, Leaf } from "lucide-react"
import { useCallback } from "react"
import { Link, useParams } from "react-router-dom"
import { fetchPlant, type ApiPlantDetail } from "../api/plants"
import { BotanicalImage, StatusPill } from "../components/plants/PlantPrimitives"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

export function PlantArticlePage() {
  const { slug } = useParams()
  const plant = useAsyncResource(useCallback(async (signal: AbortSignal) => {
    if (!slug) return null
    try {
      return await fetchPlant(slug, signal)
    } catch (error) {
      if (error instanceof Error && error.message.includes("404")) return null
      throw error
    }
  }, [slug]))

  return (
    <SiteShell>
      <div id="top" className="bg-paper text-deep">
        {plant.isLoading ? <RouteState eyebrow="HerbWire / loading" title="Loading this plant profile." description="The encyclopedia article is being retrieved from FastAPI and PostgreSQL." primaryAction={{ label: "Return to plants", to: "/plants" }} /> : null}
        {plant.error ? <RouteState eyebrow="HerbWire / interrupted" title="This plant profile is temporarily unavailable." description="The requested plant article could not be loaded right now." primaryAction={{ label: "Try again", onClick: plant.reload }} secondaryAction={{ label: "Browse plants", to: "/plants" }} /> : null}
        {!plant.isLoading && !plant.error && !plant.data ? <RouteState eyebrow="HerbWire / profile not found" title="That plant is not in the public encyclopedia." description="The slug does not match a published HerbWire plant profile." primaryAction={{ label: "Browse plants", to: "/plants" }} secondaryAction={{ label: "Return home", to: "/" }} /> : null}
        {plant.data ? <PlantArticleContent plant={plant.data} /> : null}
        <Footer />
      </div>
    </SiteShell>
  )
}

function PlantArticleContent({ plant }: { plant: ApiPlantDetail }) {
  return (
    <main>
      <div className="hw-container pt-10 md:pt-16">
        <Link to="/plants" className="inline-flex items-center gap-2 font-sans text-[10px] font-bold uppercase tracking-[.16em] text-leaf hover:text-deep"><ArrowLeft size={14} /> Back to plants</Link>
        <div className="mx-auto max-w-4xl py-12 text-center md:py-20">
          <p className="hw-eyebrow flex flex-wrap items-center justify-center gap-2"><Leaf size={13} /> Published plant profile</p>
          <h1 className="mt-5 font-serif text-[clamp(3rem,8vw,7.5rem)] font-semibold leading-[.86] tracking-[-.075em]">{plant.display_common_name}</h1>
          <p className="mx-auto mt-5 font-serif text-xl italic leading-relaxed text-muted md:text-2xl">{plant.accepted_scientific_name}</p>
          <p className="mx-auto mt-7 max-w-2xl font-serif text-xl leading-relaxed text-muted md:text-2xl">{plant.introduction}</p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3 font-sans text-[11px] text-muted">
            <span>{plant.family_name ?? "Family under review"}</span><span aria-hidden="true">/</span><span>{plant.source_count} sources</span><span aria-hidden="true">/</span><span>{plant.status}</span>
          </div>
          <div className="mt-6 flex flex-wrap justify-center gap-2"><StatusPill>{plant.status}</StatusPill>{plant.parts_used.map((part) => <span key={part} className="rounded-full border border-line px-3 py-1 font-sans text-[10px] font-semibold uppercase tracking-[.12em] text-forest">{part}</span>)}</div>
        </div>
        <figure>
          <BotanicalImage label={plant.display_common_name} />
          <figcaption className="mx-auto max-w-3xl py-3 font-sans text-[10px] uppercase tracking-[.13em] text-muted">{plant.hero_image.label ?? "Botanical fallback"} / {plant.hero_image.attribution ?? "HerbWire local placeholder"} / {plant.hero_image.license_status ?? "No external image used."}</figcaption>
        </figure>
      </div>
      <article className="hw-container py-14 md:py-24">
        <div className="mx-auto max-w-2xl">
          <ArticleSection eyebrow="Overview" body={plant.summary} first />
          <ArticleSection title="Botanical identity" body={plant.botanical_description} />
          <ArticleSection title="Parts traditionally used" body={plant.parts_used.length ? plant.parts_used.join(", ") : "No plant parts are published for this profile yet."} />
          <section className="mt-12"><h2 className="font-serif text-4xl font-semibold tracking-[-.05em]">Qualified traditional uses</h2>{plant.traditional_uses.length ? plant.traditional_uses.map((use) => <div key={`${use.tradition}-${use.statement}`} className="mt-6 border-l-2 border-gold pl-5"><p className="hw-eyebrow">{use.tradition}</p><p className="mt-3 font-serif text-lg leading-[1.8] text-muted">{use.statement}</p><p className="mt-2 font-sans text-xs leading-relaxed text-muted">{use.limitation}</p></div>) : <p className="mt-6 font-serif text-lg leading-[1.8] text-muted">No traditional-use statements are published for this profile yet.</p>}</section>
          <ArticleSection title="Geographical distribution" body={plant.distribution.length ? plant.distribution.join("; ") : "Distribution details are not published yet."} />
          <ArticleSection title="Preparation traditions" body={plant.preparation || "Preparation traditions are not published for this profile."} />
          <ArticleSection title="Evidence and limitations" body={plant.evidence_notes} />
          <section className="mt-14 border-t-2 border-forest pt-5"><p className="hw-eyebrow">Safety note</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.05em]">Safety and contraindications</h2><p className="mt-3 font-serif text-lg leading-relaxed text-muted">HerbWire is an encyclopedia. It does not diagnose, prescribe, recommend dosage, or replace care from a qualified professional.</p>{plant.safety_notes.length ? <ul className="mt-4 grid gap-3 font-serif text-lg leading-relaxed text-muted">{plant.safety_notes.map((note) => <li key={note}>{note}</li>)}</ul> : <p className="mt-3 font-serif text-lg leading-relaxed text-muted">No safety notes are published yet.</p>}</section>
          <section className="mt-14 border-t-2 border-forest pt-5" id="sources"><p className="hw-eyebrow">Sources</p><div className="mt-5 grid gap-4">{plant.sources.map((source, index) => <div key={source.id} className="border-b border-line pb-4 last:border-b-0 last:pb-0"><p className="font-serif text-xl font-semibold tracking-[-.03em] text-deep">{source.title}</p><div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 font-sans text-xs uppercase tracking-[.11em] text-muted"><span>{source.publisher}</span><span>{source.source_type}</span><span>{source.original_language}</span><span>{source.license_status}</span></div><a href={source.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link">Open source <ExternalLink size={14} /></a>{index < plant.sources.length - 1 ? null : null}</div>)}</div></section>
          <section className="mt-14 border-t border-line pt-5"><p className="hw-eyebrow">Publication</p><p className="mt-3 font-sans text-sm leading-relaxed text-muted">Status: {plant.status}{plant.published_at ? ` / Published ${new Date(plant.published_at).toLocaleString()}` : " / Not published"}</p></section>
        </div>
      </article>
    </main>
  )
}

function ArticleSection({ title, eyebrow, body, first = false }: { title?: string; eyebrow?: string; body: string; first?: boolean }) {
  if (first) return <section><p className="hw-eyebrow">{eyebrow}</p><p className="mt-4 font-serif text-2xl leading-relaxed first-letter:text-6xl first-letter:font-semibold first-letter:leading-[.8] first-letter:text-leaf">{body}</p></section>
  return <section className="mt-12">{title ? <h2 className="font-serif text-4xl font-semibold tracking-[-.05em]">{title}</h2> : null}<p className="mt-6 font-serif text-lg leading-[1.8] text-muted">{body}</p></section>
}
