import { ArrowLeft, ExternalLink, Leaf, MapIcon } from "lucide-react"
import { useCallback } from "react"
import { Link, useParams } from "react-router-dom"
import { fetchPlant, type ApiPlantDetail } from "../api/plants"
import { BotanicalImage, PlantDistributionMap, StatusPill } from "../components/plants/PlantPrimitives"
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
  const media = plant.hero_image
  const informationSources = plant.sources.filter((source) => source.source_type !== "licensed_media")
  return (
    <main>
      <div className="hw-container pt-10 md:pt-16">
        <Link to="/plants" className="inline-flex items-center gap-2 font-sans text-[10px] font-bold uppercase tracking-[.16em] text-leaf hover:text-deep"><ArrowLeft size={14} /> Back to plants</Link>
        <div className="mx-auto max-w-4xl py-12 text-center md:py-20">
          <p className="hw-eyebrow flex flex-wrap items-center justify-center gap-2"><Leaf size={13} /> Published plant profile</p>
          <h1 className="mt-5 font-serif text-[clamp(3rem,8vw,7.5rem)] font-semibold leading-[.86] tracking-[-.075em]">{plant.display_common_name}</h1>
          <p className="mx-auto mt-5 font-serif text-xl italic leading-relaxed text-muted md:text-2xl">{plant.accepted_scientific_name}</p>
          <p className="mx-auto mt-7 max-w-2xl font-serif text-xl leading-relaxed text-muted md:text-2xl">{plant.summary}</p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3 font-sans text-[11px] text-muted">
            <span>{plant.family_name ?? "Family under review"}</span><span aria-hidden="true">/</span><span>{plant.growth_form || "Growth form unavailable"}</span><span aria-hidden="true">/</span><span>{plant.source_count} sources</span>
          </div>
          <div className="mt-6 flex flex-wrap justify-center gap-2"><StatusPill>{plant.status}</StatusPill>{plant.parts_used.map((part) => <span key={part} className="rounded-full border border-line px-3 py-1 font-sans text-[10px] font-semibold uppercase tracking-[.12em] text-forest">{part}</span>)}</div>
        </div>
        <figure>
          <BotanicalImage label={plant.display_common_name} image={media} />
          <figcaption className="mx-auto max-w-3xl py-3 font-sans text-[10px] uppercase tracking-[.13em] text-muted">
            <span>{media.caption ?? plant.display_common_name}</span>
            {media.attribution ? <span> / {media.attribution}</span> : <span> / Botanical fallback</span>}
            {media.source_page ? <a href={media.source_page} target="_blank" rel="noreferrer" className="ml-2 font-bold text-leaf hover:text-forest">File page <ExternalLink className="inline" size={12} /></a> : null}
            {media.license_url && media.license ? <a href={media.license_url} target="_blank" rel="noreferrer" className="ml-2 font-bold text-leaf hover:text-forest">{media.license}</a> : null}
          </figcaption>
        </figure>
      </div>
      <article className="hw-container py-14 md:py-24">
        <div className="mx-auto max-w-2xl">
          <ArticleOverview plant={plant} />
          <ArticleSection title="Botanical identity" body={plant.botanical_description} />
          {plant.known_synonyms.length ? <ArticleSection title="Known synonyms" body={plant.known_synonyms.join("; ")} /> : null}
          <ArticleSection title="Parts traditionally used" body={plant.parts_used.length ? plant.parts_used.join(", ") : "No plant parts are published for this profile yet."} />
          <section className="mt-12"><h2 className="font-serif text-4xl font-semibold tracking-[-.05em]">Qualified traditional uses</h2>{plant.traditional_uses.length ? plant.traditional_uses.map((use) => <div key={use.tradition + use.statement} className="mt-6 border-l-2 border-gold pl-5"><p className="hw-eyebrow">{use.tradition}</p><p className="mt-3 font-serif text-lg leading-[1.8] text-muted">{use.statement}</p><p className="mt-2 font-sans text-xs leading-relaxed text-muted">{use.limitation}</p></div>) : <p className="mt-6 font-serif text-lg leading-[1.8] text-muted">No traditional-use statements are published for this profile yet.</p>}</section>
          <DistributionSection plant={plant} />
          <ArticleSection title="Preparation traditions" body={plant.preparation || "Preparation traditions are not published for this profile."} />
          <RichArticleDetails plant={plant} />
          <section className="mt-14 border-t-2 border-forest pt-5"><p className="hw-eyebrow">Safety note</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.05em]">Safety and contraindications</h2><p className="mt-3 font-serif text-lg leading-relaxed text-muted">HerbWire is an encyclopedia. It does not diagnose, prescribe, recommend dosage, or replace care from a qualified professional.</p>{plant.safety_notes.length ? <ul className="mt-5 grid gap-4">{plant.safety_notes.map((note) => <li key={note.category + note.statement} className="border-l-2 border-rust pl-4"><span className="hw-eyebrow">{note.category}</span><p className="mt-2 font-serif text-lg leading-relaxed text-muted">{note.statement}</p></li>)}</ul> : <p className="mt-3 font-serif text-lg leading-relaxed text-muted">No safety notes are published yet.</p>}</section>
          <section className="mt-14 border-t-2 border-forest pt-5" id="sources"><p className="hw-eyebrow">Sources</p><div className="mt-5 grid gap-4">{informationSources.map((source) => <div key={source.id} className="border-b border-line pb-4 last:border-b-0 last:pb-0"><p className="font-serif text-xl font-semibold tracking-[-.03em] text-deep">{source.title}</p><div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 font-sans text-xs uppercase tracking-[.11em] text-muted"><span>{source.publisher}</span><span>{source.source_type}</span><span>{source.original_language}</span><span>{source.license_status}</span></div><a href={source.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link">Open source <ExternalLink size={14} /></a></div>)}</div></section>
          <section className="mt-14 border-t border-line pt-5"><p className="hw-eyebrow">Publication</p><p className="mt-3 font-sans text-sm leading-relaxed text-muted">Status: {plant.status}{plant.published_at ? " / Published " + new Date(plant.published_at).toLocaleString() : " / Not published"}{plant.last_reviewed_at ? " / Last reviewed " + new Date(plant.last_reviewed_at).toLocaleDateString() : ""}</p></section>
        </div>
      </article>
    </main>
  )
}


function SourceLinks({ ids, plant }: { ids: string[]; plant: ApiPlantDetail }) {
  const sources = ids.map((id) => plant.sources.find((source) => source.external_identifier === id)).filter(Boolean)
  return <div className="mt-3 flex flex-wrap gap-2">{sources.map((source) => source ? <a key={source.id} href={source.url} target="_blank" rel="noreferrer" className="font-sans text-[10px] font-bold uppercase tracking-[.1em] text-leaf hw-link">{source.publisher}: {source.title} <ExternalLink className="inline" size={11} /></a> : null)}</div>
}

function RichArticleDetails({ plant }: { plant: ApiPlantDetail }) {
  const details = plant.article_details
  const preparationForms = details?.preparation_forms ?? []
  const evidenceFindings = details?.evidence_findings ?? []
  const mechanisms = details?.mechanisms ?? []
  const specialPopulations = details?.special_populations ?? []
  const interactions = details?.interactions ?? []
  if (!(preparationForms.length || evidenceFindings.length || mechanisms.length || specialPopulations.length || interactions.length)) return null
  return <>
    {preparationForms.length ? <section className="mt-12"><h2 className="font-serif text-4xl font-semibold tracking-[-.05em]">Preparation and product forms</h2><div className="mt-6 grid gap-5">{preparationForms.map((form) => <article key={form.label} className="border border-line bg-sage/10 p-5"><p className="hw-eyebrow">{form.route} / {form.plant_part}</p><h3 className="mt-2 font-serif text-2xl font-semibold">{form.label}</h3><p className="mt-3 font-serif text-lg leading-relaxed text-muted">{form.description}</p><p className="mt-3 border-l-2 border-gold pl-3 font-sans text-xs leading-relaxed">{form.equivalence_warning}</p><SourceLinks ids={form.source_ids} plant={plant} /></article>)}</div></section> : null}
    {evidenceFindings.length ? <section className="mt-14"><p className="hw-eyebrow">What the evidence says</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.05em]">What have we learned?</h2><div className="mt-6 grid gap-5">{evidenceFindings.map((finding) => <article key={finding.heading} className="border-b border-line pb-5"><p className="hw-eyebrow">{finding.evidence_level.replace("_", " ")} / {finding.preparation}</p><h3 className="mt-2 font-serif text-2xl font-semibold">{finding.heading}</h3><p className="mt-3 font-serif text-lg leading-relaxed text-muted">{finding.summary}</p><p className="mt-3 font-sans text-sm leading-relaxed text-muted"><strong className="text-deep">Limitations:</strong> {finding.limitations}</p><SourceLinks ids={finding.source_ids} plant={plant} /></article>)}</div></section> : null}
    {mechanisms.length ? <section className="mt-12"><h2 className="font-serif text-4xl font-semibold tracking-[-.05em]">How it may work</h2><div className="mt-6 grid gap-4">{mechanisms.map((item) => <article key={item.preparation} className="border-l-2 border-leaf pl-5"><p className="hw-eyebrow">{item.preparation}</p><p className="mt-3 font-serif text-lg leading-relaxed text-muted">{item.summary}</p><p className="mt-2 font-sans text-xs leading-relaxed text-muted">{item.qualification}</p><SourceLinks ids={item.source_ids} plant={plant} /></article>)}</div></section> : null}
    {specialPopulations.length || interactions.length ? <section className="mt-14 border-t-2 border-rust pt-5"><p className="hw-eyebrow">Additional caution</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.05em]">Who should avoid it or seek advice?</h2><div className="mt-6 grid gap-4">{specialPopulations.map((item) => <article key={item.population} className="border border-rust/30 bg-rust/5 p-5"><h3 className="font-serif text-xl font-semibold">{item.population}</h3><p className="mt-2 font-serif text-lg leading-relaxed text-muted">{item.guidance}</p><SourceLinks ids={item.source_ids} plant={plant} /></article>)}</div>{interactions.length ? <div className="mt-8"><h3 className="font-serif text-2xl font-semibold">Interactions</h3>{interactions.map((item) => <article key={item.interaction} className="mt-4 border-l-2 border-gold pl-5"><p className="font-serif text-xl font-semibold">{item.interaction}</p><p className="mt-2 font-serif text-lg leading-relaxed text-muted">{item.statement}</p><p className="mt-2 hw-eyebrow">{item.evidence_level}</p><SourceLinks ids={item.source_ids} plant={plant} /></article>)}</div> : null}</section> : null}
  </>
}

function DistributionSection({ plant }: { plant: ApiPlantDetail }) {
  const tone = { native: "bg-leaf", introduced: "bg-gold", unknown: "bg-muted" }
  const hasMap = plant.distribution.some((region) => region.map_countries?.length)

  return <section className="mt-12">
    <h2 className="font-serif text-4xl font-semibold tracking-[-.05em]">Geographical distribution</h2>
    <p className="mt-6 font-serif text-lg leading-[1.8] text-muted">{plant.distribution_summary || "A complete distribution summary is unavailable."}</p>
    {hasMap ? <PlantDistributionMap plant={plant} /> : <p className="mt-4 inline-flex items-center gap-2 font-sans text-xs leading-relaxed text-muted"><MapIcon size={15} /> A verified country-level map is not available for this profile yet; the sourced botanical-region text remains the authoritative fallback.</p>}
    {plant.distribution.length ? <><div aria-label="Distribution legend" className="mt-5 flex flex-wrap gap-4 font-sans text-xs text-muted">{(["native", "introduced", "unknown"] as const).map((status) => <span key={status} className="inline-flex items-center gap-2 capitalize"><span className={"h-2.5 w-2.5 rounded-full " + tone[status]} />{status}</span>)}</div><ul className="mt-4 grid gap-3">{plant.distribution.map((region) => <li key={region.status + region.code} className="flex gap-3 border border-line bg-sage/10 p-4"><span className={"mt-1 h-2.5 w-2.5 shrink-0 rounded-full " + tone[region.status]} /><div><p className="font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">{region.status}</p><p className="mt-1 font-serif text-base leading-relaxed text-muted">{region.name}</p></div></li>)}</ul></> : null}
  </section>
}

function ArticleOverview({ plant }: { plant: ApiPlantDetail }) {
  return <section data-testid="article-overview">
    <p className="hw-eyebrow">Overview</p>
    <div className="mt-4 font-serif text-xl leading-[1.8] text-muted">
      <p className="text-2xl first-letter:text-6xl first-letter:font-semibold first-letter:leading-[.8] first-letter:text-leaf">{plant.introduction}</p>
      <aside className="mt-9 border-y border-line bg-sage/15 px-6 py-7 md:px-8">
        <p className="hw-eyebrow">Evidence snapshot</p>
        <h2 className="mt-2 font-serif text-3xl font-semibold tracking-[-.04em] text-deep">How Much Do We Know?</h2>
        <p className="mt-4 text-lg leading-[1.8]">{plant.evidence_notes}</p>
      </aside>
    </div>
  </section>
}

function ArticleSection({ title, body }: { title: string; body: string }) {
  return <section className="mt-12"><h2 className="font-serif text-4xl font-semibold tracking-[-.05em]">{title}</h2><p className="mt-6 font-serif text-lg leading-[1.8] text-muted">{body}</p></section>
}
