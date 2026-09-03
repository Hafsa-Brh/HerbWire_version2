import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { decideDiscovery, fetchDiscoveryReviews, type ApiDiscoveryArticle } from "../../api/discoveries"
import { DiscoveryBotanicalDistribution, DiscoveryResearchGeography } from "../../components/discoveries/DiscoveryMaps"
import { useAsyncResource } from "../../hooks/useAsyncResource"
import { AdminStateCard, AdminStatusPill, PageHeader, Panel } from "./AdminPrimitives"

const DETAIL_PAGES = [
  { title: "Overview", keys: ["overview", "botanical_identity"] },
  { title: "Research", keys: ["research_question", "traditional_context", "why_studied", "methods", "evidence_base", "preparation", "outcomes"] },
  { title: "Findings and evidence", keys: ["findings", "why_matters", "evidence_strength", "limitations", "related_research", "cannot_conclude"] },
  { title: "Safety, geography, and provenance", keys: ["safety", "botanical_distribution"] },
] as const

function EvidenceView({ article, detailPage }: { article: ApiDiscoveryArticle; detailPage: number }) {
  const plant = article.linked_plants?.[0]
  const identity = article.botanical_identity
  const active = DETAIL_PAGES[detailPage - 1]
  const blocks = article.body_blocks.filter((block) => block.key && active.keys.includes(block.key as never))
  return <div className="grid gap-6">
    {detailPage === 1 ? <>
      <div className="flex flex-wrap gap-2"><AdminStatusPill>{article.review_status ?? article.status}</AdminStatusPill><AdminStatusPill>{article.qa_payload.passed ? "QA passed" : "QA held"}</AdminStatusPill></div>
      <div><p className="hw-eyebrow">Headline and deck</p><h3 className="mt-2 font-serif text-3xl font-semibold text-deep">{article.headline}</h3><p className="mt-3 font-serif text-lg leading-relaxed text-muted">{article.standfirst}</p></div>
      {article.hero_image?.local_path ? <figure><img src={article.hero_image.local_path} alt={article.hero_image.alt_text || "Discovery editorial cover"} className="aspect-[16/7] w-full rounded-xl object-cover" /><figcaption className="mt-2 font-sans text-[10px] uppercase tracking-[.1em] text-muted">{article.hero_image.caption} / {article.hero_image.attribution} / {article.hero_image.license}</figcaption></figure> : null}
      {plant ? <div><p className="hw-eyebrow">Linked plant</p><p className="mt-2 font-serif text-lg text-deep">{plant.common_name} / <i>{plant.scientific_name}</i></p></div> : identity ? <div><p className="hw-eyebrow">Standalone botanical identity</p><p className="mt-2 font-serif text-lg text-deep">{identity.common_name} / <i>{identity.accepted_scientific_name}</i></p><a className="font-sans text-xs text-leaf underline" href={identity.authority_url} target="_blank" rel="noreferrer">{identity.family} / verified taxonomy</a></div> : null}
      <dl className="grid gap-3 border-y border-line py-4 font-sans text-sm text-muted sm:grid-cols-2"><div><dt className="font-bold text-deep">Study type</dt><dd>{article.article_type ?? article.category}</dd></div><div><dt className="font-bold text-deep">Journal</dt><dd>{article.sources[0]?.journal ?? "Not reported"}</dd></div><div><dt className="font-bold text-deep">Source publication</dt><dd>{article.sources[0]?.publication_date ?? "Not reported"}</dd></div><div><dt className="font-bold text-deep">Editorial version</dt><dd>Version {article.version} / {article.content_origin}</dd></div></dl>
    </> : null}
    {detailPage === 2 ? <dl className="grid gap-4 border border-line bg-sage/10 p-5 font-sans text-sm text-muted sm:grid-cols-2"><Meta label="Research question" value={article.research_question} /><Meta label="Research context" value={article.research_context} /><Meta label="Study design" value={article.study_design} /><Meta label="Population, sample, model, or evidence base" value={article.evidence_base} /><Meta label="Intervention or exposure" value={article.intervention} /><Meta label="Comparator" value={article.comparator} /></dl> : null}
    {detailPage === 3 ? <><Meta label="Evidence-strength assessment" value={article.evidence_strength_rationale} /><Meta label="Practical interpretation" value={article.practical_interpretation} />{article.limitations.length ? <List label="Important limitations" items={article.limitations} /> : null}{article.cannot_conclude.length ? <List label="What cannot be concluded" items={article.cannot_conclude} /> : null}</> : null}
    {blocks.map((block) => block.heading && block.text ? <section key={block.key ?? block.heading} className="border-l-2 border-sage pl-4"><h3 className="font-serif text-xl font-semibold">{block.heading}</h3><p className="mt-2 font-sans text-sm leading-relaxed text-muted">{block.text}</p>{block.evidence_locations?.length ? <p className="mt-2 font-sans text-[10px] uppercase tracking-[.1em] text-muted">Trace: {block.evidence_locations.join("; ")}</p> : null}</section> : null)}
    {detailPage === 4 ? <>
      <Meta label="Safety and interaction context" value={article.safety_context} />
      <DiscoveryBotanicalDistribution article={article} />
      <DiscoveryResearchGeography article={article} />
      {article.evidence_package.excerpts?.length ? <div><p className="hw-eyebrow">Traceable source excerpts</p><ul className="mt-2 grid gap-2">{article.evidence_package.excerpts.map((excerpt, index) => <li key={index} className="border-l-2 border-sage pl-3 font-sans text-sm text-muted">{excerpt.text} <span className="text-xs">({excerpt.location})</span></li>)}</ul></div> : null}
      <div><p className="hw-eyebrow">Information sources</p><ul className="mt-2 grid gap-3">{article.sources.map((source) => <li key={source.id}><a className="font-serif text-lg text-leaf underline" href={source.canonical_url} target="_blank" rel="noreferrer">{source.title}</a><span className="block font-sans text-xs text-muted">{source.support_role.replaceAll("_", " ")} / {source.pmid ? `PMID ${source.pmid}` : source.external_identifier}{source.doi ? ` / DOI ${source.doi}` : ""}{source.journal ? ` / ${source.journal}` : ""}</span></li>)}</ul></div>
      <div><p className="hw-eyebrow">Separate media attribution</p><p className="mt-2 font-sans text-sm text-muted">{article.hero_image.attribution} / {article.hero_image.license} / {article.hero_image.caption}</p></div>
      <dl className="grid gap-2 border-t border-line pt-4 font-sans text-xs text-muted sm:grid-cols-2"><div><dt>Created</dt><dd>{new Date(article.created_at).toLocaleString()}</dd></div><div><dt>Reviewed</dt><dd>{article.reviewed_at ? new Date(article.reviewed_at).toLocaleString() : "Not yet"}</dd></div><div><dt>Published</dt><dd>{article.published_at ? new Date(article.published_at).toLocaleString() : "Not published"}</dd></div><div><dt>Publication readiness</dt><dd>{article.status === "approved" ? "Approved version is eligible for separate publication" : article.status === "published" ? "Published" : "Requires editorial decision"}</dd></div></dl>
    </> : null}
  </div>
}

function Meta({ label, value }: { label: string; value?: string | null }) { return value ? <div><p className="hw-eyebrow">{label}</p><p className="mt-2 font-sans text-sm leading-relaxed text-muted">{value}</p></div> : null }
function List({ label, items }: { label: string; items: string[] }) { return <div><p className="hw-eyebrow">{label}</p><ul className="mt-2 list-disc pl-5 font-sans text-sm leading-relaxed text-muted">{items.map((item) => <li key={item}>{item}</li>)}</ul></div> }

export function DiscoveryReviewQueue() {
  const data = useAsyncResource(useCallback((signal: AbortSignal) => fetchDiscoveryReviews(signal), []))
  const articles = useMemo(() => data.data?.items ?? [], [data.data])
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get("article")
  const detailPage = Math.min(4, Math.max(1, Number(searchParams.get("detail_page") ?? "1") || 1))
  const [page, setPage] = useState(1)
  const [reason, setReason] = useState("Needs additional evidence review.")
  const [message, setMessage] = useState("")
  const [pending, setPending] = useState(false)
  const [query, setQuery] = useState("")
  const [batch, setBatch] = useState("all")
  const headingRef = useRef<HTMLHeadingElement>(null)
  const shouldFocus = useRef(false)
  const filteredArticles = articles.filter((article) => {
    const identity = article.linked_plants?.[0]?.common_name ?? article.botanical_identity?.common_name ?? ""
    return `${article.headline} ${identity}`.toLowerCase().includes(query.trim().toLowerCase()) && (batch === "all" || article.evidence_package.batch_id === batch)
  })
  const pageCount = Math.max(1, Math.ceil(filteredArticles.length / 6))
  const safePage = Math.min(page, pageCount)
  const pageArticles = filteredArticles.slice((safePage - 1) * 6, safePage * 6)
  const selected = filteredArticles.find((item) => item.id === selectedId) ?? pageArticles[0] ?? null

  useEffect(() => { if (shouldFocus.current) { headingRef.current?.focus(); shouldFocus.current = false } }, [detailPage, selected?.id])
  function navigateDetail(articleId: string, nextPage: number) { const next = new URLSearchParams(searchParams); next.set("article", articleId); if (nextPage > 1) next.set("detail_page", String(nextPage)); else next.delete("detail_page"); setSearchParams(next) }
  function selectArticle(articleId: string) { setMessage(""); navigateDetail(articleId, 1) }
  function setDetailPage(nextPage: number) { if (!selected || nextPage === detailPage || nextPage < 1 || nextPage > 4) return; shouldFocus.current = true; navigateDetail(selected.id, nextPage) }

  async function decide(action: "approve" | "hold" | "reject" | "publish") {
    if (!selected || pending) return
    const targetArticle = selected
    const target = action === "approve" ? "approved" : action === "publish" ? "published" : action === "hold" ? "held" : "rejected"
    if (!window.confirm(`Confirm: ${targetArticle.headline} version ${targetArticle.version}: ${targetArticle.status} → ${target}?`)) return
    setPending(true); setMessage("")
    try { await decideDiscovery(targetArticle.id, action, action === "approve" || action === "publish" ? undefined : reason); setMessage(action === "publish" ? "Discovery published after its separate approval." : action === "approve" ? "Discovery approved; publication remains a separate action." : action === "hold" ? "Discovery held and remains non-public." : "Discovery rejected and remains non-public."); data.reload() }
    catch { setMessage("The editorial action was rejected or could not be saved.") }
    finally { setPending(false) }
  }

  return <><PageHeader eyebrow="Editorial / curated discovery" title="Discovery Review" description="Inspect source traceability, evidence limits, safety language, maps, and media before approving. Publication is always separate." action={<button type="button" onClick={data.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Refresh</button>} />
    {data.isLoading ? <AdminStateCard title="Loading discovery drafts" description="Loading review-ready, approved, held, and published discoveries." /> : null}
    {data.error ? <AdminStateCard title="Discovery queue unavailable" description="The authenticated review queue could not be loaded." action={<button type="button" onClick={data.reload}>Try again</button>} /> : null}
    {data.data && !articles.length ? <AdminStateCard title="No discovery drafts" description="No discoveries are available for editorial inspection." /> : null}
    {selected ? <section aria-label="Discovery review workspace" className="grid items-start gap-5 lg:grid-cols-[.7fr_1.3fr]">
      <Panel eyebrow="Private queue" title="Review drafts" className="lg:sticky lg:top-24"><div className="mb-4 grid gap-2 sm:grid-cols-2"><input aria-label="Search discovery drafts" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1) }} placeholder="Search plant or headline" className="border border-line bg-paper px-3 py-2 font-sans text-sm" /><select aria-label="Filter discovery batch" value={batch} onChange={(event) => { setBatch(event.target.value); setPage(1) }} className="border border-line bg-paper px-3 py-2 font-sans text-sm"><option value="all">All batches</option><option value="milestone-4b">Original ten</option><option value="milestone-4c-new-plants">New twelve</option></select></div><div className="grid gap-3">{pageArticles.map((article) => <button key={article.id} type="button" disabled={pending} aria-pressed={selected.id === article.id} onClick={() => selectArticle(article.id)} className={`border p-4 text-left disabled:opacity-50 ${selected.id === article.id ? "border-leaf bg-sage/25" : "border-line"}`}><AdminStatusPill>{article.review_status ?? article.status}</AdminStatusPill><h2 className="mt-3 font-serif text-xl font-semibold text-deep">{article.headline}</h2><p className="mt-2 font-sans text-xs text-muted">{article.linked_plants?.[0]?.common_name ?? article.botanical_identity?.common_name ?? article.category} / {article.evidence_package.batch_id === "milestone-4c-new-plants" ? "new twelve" : "original ten"} / v{article.version}</p></button>)}</div><div className="mt-5 flex items-center justify-between border-t border-line pt-4"><button type="button" aria-label="Previous discovery page" disabled={safePage === 1 || pending} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button><span className="font-sans text-xs text-muted">Page {safePage} of {pageCount}</span><button type="button" aria-label="Next discovery page" disabled={safePage === pageCount || pending} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>Next</button></div></Panel>
      <Panel eyebrow="Draft detail" title={selected.headline} className="min-w-0"><nav aria-label="Discovery detail pages" className="mb-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{DETAIL_PAGES.map((item, index) => <button key={item.title} type="button" aria-current={detailPage === index + 1 ? "page" : undefined} onClick={() => setDetailPage(index + 1)} className={`border px-3 py-2 text-left font-sans text-xs font-semibold ${detailPage === index + 1 ? "border-leaf bg-sage/25 text-forest" : "border-line text-muted"}`}>{index + 1}. {item.title}</button>)}</nav><div aria-live="polite"><p className="font-sans text-xs text-muted">Detail page {detailPage} of 4.</p><h2 ref={headingRef} tabIndex={-1} className="mt-2 font-serif text-2xl font-semibold text-deep outline-none">{DETAIL_PAGES[detailPage - 1].title}</h2></div><div className="mt-5"><EvidenceView article={selected} detailPage={detailPage} /></div><div className="mt-6 flex items-center justify-between border-t border-line pt-4"><button type="button" aria-label="Previous detail page" disabled={detailPage === 1} onClick={() => setDetailPage(detailPage - 1)}>Previous</button><span className="font-sans text-xs text-muted">Detail page {detailPage} of 4</span><button type="button" aria-label="Next detail page" disabled={detailPage === 4} onClick={() => setDetailPage(detailPage + 1)}>Next</button></div>{message ? <p role="alert" className="mt-4 bg-gold/10 p-3 font-sans text-sm">{message}</p> : null}<div className="sticky bottom-0 mt-6 border-t-2 border-forest bg-paper/95 py-5 backdrop-blur"><p className="mb-3 font-sans text-xs font-semibold text-deep">Actions for: {selected.headline} / version {selected.version}</p><label className="grid gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">Hold or reject reason<input value={reason} onChange={(event) => setReason(event.target.value)} className="min-h-11 border border-line bg-paper px-3 font-sans text-sm font-normal normal-case tracking-normal" /></label><div className="mt-4 flex flex-wrap gap-3"><button type="button" onClick={() => decide("approve")} disabled={pending || selected.status !== "needs_review"} className="bg-forest px-4 py-3 text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">Approve</button><button type="button" onClick={() => decide("publish")} disabled={pending || selected.status !== "approved"} className="bg-leaf px-4 py-3 text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">Publish approved version</button><button type="button" onClick={() => decide("hold")} disabled={pending || selected.status === "published"} className="border border-rust px-4 py-3 text-xs font-bold uppercase tracking-[.1em] text-rust disabled:opacity-40">Hold</button><button type="button" onClick={() => decide("reject")} disabled={pending || selected.status === "published"} className="bg-rust px-4 py-3 text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">Reject</button></div></div></Panel>
    </section> : null}</>
}
