import { ArrowLeft, ExternalLink, FlaskConical } from "lucide-react"
import { useCallback } from "react"
import { Link, useParams } from "react-router-dom"
import { fetchPublishedDiscovery, type ApiPublicDiscoveryArticle } from "../api/discoveries"
import { ApiRequestError } from "../api/plants"
import { DiscoveryBotanicalDistribution, DiscoveryResearchGeography } from "../components/discoveries/DiscoveryMaps"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

export function DiscoveryArticlePage() {
  const { slug } = useParams()
  const discovery = useAsyncResource(useCallback(async (signal: AbortSignal) => {
    if (!slug) return null
    try { return await fetchPublishedDiscovery(slug, signal) }
    catch (error) { if (error instanceof ApiRequestError && error.status === 404) return null; throw error }
  }, [slug]))
  return <SiteShell><main id="top">
    {discovery.isLoading ? <RouteState eyebrow="HerbWire / discovery" title="Loading this discovery." description="Retrieving the reviewed public article." primaryAction={{ label: "All discoveries", to: "/discoveries" }} /> : null}
    {discovery.error ? <RouteState eyebrow="HerbWire / interrupted" title="This discovery is temporarily unavailable." description="The article could not be loaded." primaryAction={{ label: "Try again", onClick: discovery.reload }} secondaryAction={{ label: "All discoveries", to: "/discoveries" }} /> : null}
    {!discovery.isLoading && !discovery.error && !discovery.data ? <RouteState eyebrow="HerbWire / not found" title="That discovery is not published." description="Private editorial drafts never appear in the public archive." primaryAction={{ label: "All discoveries", to: "/discoveries" }} /> : null}
    {discovery.data ? <DiscoveryContent article={discovery.data} /> : null}
  </main><Footer /></SiteShell>
}

function DiscoveryContent({ article }: { article: ApiPublicDiscoveryArticle }) {
  const linkedPlant = article.linked_plants?.[0]
  const plant = linkedPlant ?? (article.botanical_identity ? {
    common_name: article.botanical_identity.common_name,
    scientific_name: article.botanical_identity.accepted_scientific_name,
  } : undefined)
  const image = article.hero_image ?? {}
  return <>
    <div className="hw-container pt-10 md:pt-16">
      <Link to="/discoveries" className="inline-flex items-center gap-2 font-sans text-[10px] font-bold uppercase tracking-[.16em] text-leaf"><ArrowLeft size={14} /> All discoveries</Link>
      <header className="mx-auto max-w-4xl py-12 text-center md:py-20">
        <p className="hw-eyebrow inline-flex items-center gap-2"><FlaskConical size={14} /> {article.article_type ?? article.category}</p>
        <h1 className="mt-5 font-serif text-[clamp(2.8rem,7vw,6.5rem)] font-semibold leading-[.9] tracking-[-.065em] text-deep">{article.headline}</h1>
        <p className="mx-auto mt-7 max-w-3xl font-serif text-xl leading-relaxed text-muted md:text-2xl">{article.standfirst}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-3 font-sans text-[10px] font-bold uppercase tracking-[.12em] text-muted">
          {plant ? <span>{plant.common_name} / <i>{plant.scientific_name}</i></span> : null}
          {article.evidence_strength ? <span>{article.evidence_strength} evidence</span> : null}
          <span>Version {article.version}</span>{article.sources[0]?.publication_date ? <span>Source published {new Date(article.sources[0].publication_date).toLocaleDateString()}</span> : null}<span>HerbWire published {new Date(article.published_at).toLocaleDateString()}</span>
        </div>
      </header>
      {image.local_path ? <figure><div className="aspect-[16/8] overflow-hidden rounded-[1.75rem] bg-sage/20"><img src={image.local_path} alt={image.alt_text || `${plant?.common_name ?? "Medicinal plant"} botanical reference`} className="h-full w-full object-cover" /></div><figcaption className="mx-auto max-w-4xl py-3 font-sans text-[10px] leading-relaxed uppercase tracking-[.12em] text-muted">{image.caption}{image.attribution ? ` / ${image.attribution}` : ""} {image.source_page ? <a href={image.source_page} target="_blank" rel="noreferrer" className="font-bold text-leaf">Image source <ExternalLink className="inline" size={11} /></a> : null} {image.license_url ? <a href={image.license_url} target="_blank" rel="noreferrer" className="font-bold text-leaf">{image.license}</a> : null}</figcaption></figure> : null}
    </div>
    <article className="hw-container py-14 md:py-24"><div className="mx-auto max-w-3xl">
      {article.body_blocks.map((block) => block.heading && block.text ? <section key={block.key ?? block.heading} className="mb-12"><h2 className="font-serif text-3xl font-semibold tracking-[-.04em] text-deep md:text-4xl">{block.heading}</h2><p className="mt-5 font-serif text-lg leading-[1.85] text-muted">{block.text}</p>{block.evidence_locations?.length ? <p className="mt-3 font-sans text-[10px] uppercase tracking-[.11em] text-muted">Trace: {block.evidence_locations.join("; ")}</p> : null}</section> : null)}
      {article.practical_interpretation ? <aside className="my-12 border-y-2 border-forest bg-sage/15 px-6 py-8"><p className="hw-eyebrow">Practical interpretation</p><p className="mt-3 font-serif text-xl leading-relaxed text-deep">{article.practical_interpretation}</p></aside> : null}
      <DiscoveryBotanicalDistribution article={article} />
      <DiscoveryResearchGeography article={article} />
      {linkedPlant ? <section className="mt-12 border-t border-line pt-7"><p className="hw-eyebrow">Related plant profile</p><Link to={`/plants/${linkedPlant.slug}`} className="mt-3 inline-flex items-center gap-2 font-serif text-2xl font-semibold text-leaf">{linkedPlant.common_name} <span className="font-normal italic text-muted">{linkedPlant.scientific_name}</span></Link></section> : article.botanical_identity ? <section className="mt-12 border-t border-line pt-7"><p className="hw-eyebrow">Verified botanical identity</p><a href={article.botanical_identity.authority_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 font-serif text-2xl font-semibold text-leaf">{article.botanical_identity.common_name} <span className="font-normal italic text-muted">{article.botanical_identity.accepted_scientific_name}</span> <ExternalLink size={14} /></a><p className="mt-2 font-sans text-xs text-muted">{article.botanical_identity.family} / no encyclopedia profile yet</p></section> : null}
      <section className="mt-14 border-t-2 border-forest pt-6"><p className="hw-eyebrow">Information sources</p><div className="mt-5 grid gap-6">{article.sources.map((source) => <article key={source.id}><a href={source.canonical_url} target="_blank" rel="noreferrer" className="font-serif text-xl font-semibold text-deep hover:text-leaf">{source.title} <ExternalLink className="inline" size={14} /></a><p className="mt-2 font-sans text-xs leading-relaxed text-muted">{source.authors.length ? `${source.authors.join(", ")}. ` : ""}{source.journal ? `${source.journal}. ` : ""}{source.pmid ? `PMID ${source.pmid}` : source.external_identifier}{source.doi ? ` / DOI ${source.doi}` : ""}.</p></article>)}</div></section>
      <section className="mt-12 border-t border-line pt-6"><p className="hw-eyebrow">Publication note</p><p className="mt-3 font-sans text-sm leading-relaxed text-muted">This evidence report is educational, not diagnosis, treatment advice, or a dosage recommendation. It was published only after separate editorial approval.</p></section>
    </div></article>
  </>
}
