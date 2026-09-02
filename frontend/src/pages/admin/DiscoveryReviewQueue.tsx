import { useCallback, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { decideDiscovery, fetchDiscoveryReviews, type ApiDiscoveryArticle } from "../../api/discoveries"
import { useAsyncResource } from "../../hooks/useAsyncResource"
import { AdminStateCard, AdminStatusPill, PageHeader, Panel } from "./AdminPrimitives"

function EvidenceView({ article }: { article: ApiDiscoveryArticle }) {
  const plant = article.linked_plants?.[0]
  return <div className="grid gap-7">
    {article.hero_image?.local_path ? <figure><img src={article.hero_image?.local_path} alt={article.hero_image?.alt_text || "Botanical reference"} className="aspect-[16/7] w-full rounded-xl object-cover" /><figcaption className="mt-2 font-sans text-[10px] uppercase tracking-[.1em] text-muted">{article.hero_image.caption} / {article.hero_image.attribution} / {article.hero_image.license}</figcaption></figure> : null}
    <div><p className="hw-eyebrow">Version and eligibility</p><p className="mt-2 font-sans text-sm text-muted">Version {article.version} / {article.content_origin} / QA {article.qa_payload.passed ? "passed" : "held"}</p></div>
    {plant ? <div><p className="hw-eyebrow">Linked plant</p><p className="mt-2 font-serif text-lg text-deep">{plant.common_name} / <i>{plant.scientific_name}</i></p></div> : null}
    <div><p className="hw-eyebrow">Source report</p><p className="mt-2 font-serif text-lg leading-relaxed text-deep">{article.standfirst}</p></div>
    {article.body_blocks.map((block) => block.heading && block.text ? <section key={block.key ?? block.heading} className="border-l-2 border-sage pl-4"><h3 className="font-serif text-xl font-semibold">{block.heading}</h3><p className="mt-2 font-sans text-sm leading-relaxed text-muted">{block.text}</p>{block.evidence_locations?.length ? <p className="mt-2 font-sans text-[10px] uppercase tracking-[.1em] text-muted">{block.evidence_locations.join("; ")}</p> : null}</section> : null)}
    {article.evidence_package.excerpts?.length ? <div><p className="hw-eyebrow">Traceable source excerpts</p><ul className="mt-2 grid gap-2">{article.evidence_package.excerpts.map((excerpt, index) => <li key={index} className="border-l-2 border-sage pl-3 font-sans text-sm text-muted">{excerpt.text} <span className="text-xs">({excerpt.location})</span></li>)}</ul></div> : null}
    {article.body_blocks.length < 11 ? <div><p className="hw-eyebrow">Limitations and safety</p><ul className="mt-2 list-disc pl-5 font-sans text-sm text-muted">{article.limitations.map((item) => <li key={item}>{item}</li>)}</ul><p className="mt-3 font-sans text-sm text-muted">{article.safety_context}</p></div> : null}    {article.geography?.length ? <div><p className="hw-eyebrow">Research geography</p>{article.geography?.map((item) => <p key={item.display_label} className="mt-2 font-sans text-sm text-muted">{item.display_label} / {item.evidence_type.replaceAll("_", " ")} / {item.qualification}</p>)}</div> : null}
    <div><p className="hw-eyebrow">Provenance</p><ul className="mt-2 grid gap-3">{article.sources.map((source) => <li key={source.id}><a className="font-serif text-lg text-leaf underline" href={source.canonical_url} target="_blank" rel="noreferrer">{source.title}</a><span className="block font-sans text-xs text-muted">PMID {source.pmid}{source.doi ? ` / DOI ${source.doi}` : ""} / {source.journal}</span></li>)}</ul></div>
  </div>
}

export function DiscoveryReviewQueue() {
  const data = useAsyncResource(useCallback((signal: AbortSignal) => fetchDiscoveryReviews(signal), []))
  const articles = useMemo(() => data.data?.items ?? [], [data.data])
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get("article"))
  const [page, setPage] = useState(1)
  const [reason, setReason] = useState("Needs additional evidence review.")
  const [message, setMessage] = useState("")
  const [pending, setPending] = useState(false)
  const pageSize = 6
  const pageCount = Math.max(1, Math.ceil(articles.length / pageSize))
  const safePage = Math.min(page, pageCount)
  const pageArticles = articles.slice((safePage - 1) * pageSize, safePage * pageSize)
  const selected = articles.find((item) => item.id === selectedId) ?? pageArticles[0] ?? null

  async function decide(action: "approve" | "hold" | "reject" | "publish") {
    if (!selected || pending) return
    const target = action === "approve" ? "approved" : action === "publish" ? "published" : action === "hold" ? "held" : "rejected"
    const label = `${selected.headline} version ${selected.version}: ${selected.status} → ${target}`
    if (!window.confirm(`Confirm: ${label}?`)) return
    setPending(true); setMessage("")
    try {
      await decideDiscovery(selected.id, action, action === "approve" || action === "publish" ? undefined : reason)
      setMessage(action === "publish" ? "Discovery published after its separate approval." : action === "approve" ? "Discovery approved; publication remains a separate action." : action === "hold" ? "Discovery held and remains non-public." : "Discovery rejected and remains non-public.")
      data.reload()
    } catch { setMessage("The editorial action was rejected or could not be saved.") }
    finally { setPending(false) }
  }

  return <>
    <PageHeader eyebrow="Editorial / curated discovery" title="Discovery Review" description="Inspect source traceability, evidence limits, safety language, and media before approving. Publication is always a separate authenticated action." action={<button type="button" onClick={data.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Refresh</button>} />
    {data.isLoading ? <AdminStateCard title="Loading discovery drafts" description="Loading review-ready, approved, held, and published discoveries." /> : null}
    {data.error ? <AdminStateCard title="Discovery queue unavailable" description="The authenticated review queue could not be loaded." action={<button type="button" onClick={data.reload}>Try again</button>} /> : null}
    {data.data && !articles.length ? <AdminStateCard title="No discovery drafts" description="No private discoveries are waiting for review." /> : null}
    {selected ? <section aria-label="Discovery review workspace" className="grid gap-5 lg:grid-cols-[.7fr_1.3fr]">
      <Panel eyebrow="Private queue" title="Review drafts"><div className="grid gap-3">{pageArticles.map((article) => <button key={article.id} type="button" aria-pressed={selected.id === article.id} onClick={() => { setSelectedId(article.id); setSearchParams({ article: article.id }) }} className={"border p-4 text-left " + (selected.id === article.id ? "border-leaf bg-sage/25" : "border-line")}><AdminStatusPill>{article.review_status ?? article.status}</AdminStatusPill><h2 className="mt-3 font-serif text-xl font-semibold text-deep">{article.headline}</h2><p className="mt-2 font-sans text-xs text-muted">{article.linked_plants?.[0]?.common_name ?? article.category} / v{article.version}</p></button>)}</div><div className="mt-5 flex items-center justify-between border-t border-line pt-4"><button type="button" aria-label="Previous discovery page" disabled={safePage === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button><span className="font-sans text-xs text-muted">Page {safePage} of {pageCount}</span><button type="button" aria-label="Next discovery page" disabled={safePage === pageCount} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>Next</button></div></Panel>
      <Panel eyebrow="Draft detail" title={selected.headline}><EvidenceView article={selected} />{message ? <p role="alert" className="mt-4 bg-gold/10 p-3 font-sans text-sm">{message}</p> : null}<div className="mt-6 border-t border-line pt-5"><label className="grid gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">Hold or reject reason<input value={reason} onChange={(event) => setReason(event.target.value)} className="min-h-11 border border-line bg-paper px-3 font-sans text-sm font-normal normal-case tracking-normal" /></label><div className="mt-4 flex flex-wrap gap-3"><button type="button" onClick={() => decide("approve")} disabled={pending || selected.status !== "needs_review"} className="bg-forest px-4 py-3 text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">Approve</button><button type="button" onClick={() => decide("publish")} disabled={pending || selected.status !== "approved"} className="bg-leaf px-4 py-3 text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">Publish approved version</button><button type="button" onClick={() => decide("hold")} disabled={pending || selected.status === "published"} className="border border-rust px-4 py-3 text-xs font-bold uppercase tracking-[.1em] text-rust disabled:opacity-40">Hold</button><button type="button" onClick={() => decide("reject")} disabled={pending || selected.status === "published"} className="bg-rust px-4 py-3 text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">Reject</button></div></div></Panel>
    </section> : null}
  </>
}