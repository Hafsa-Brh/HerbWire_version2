import { useCallback, useMemo, useState } from "react"
import {
  decideDiscovery,
  fetchDiscoveryReviews,
  type ApiDiscoveryArticle,
} from "../../api/discoveries"
import { useAsyncResource } from "../../hooks/useAsyncResource"
import { AdminStateCard, AdminStatusPill, PageHeader, Panel } from "./AdminPrimitives"

function EvidenceView({ article }: { article: ApiDiscoveryArticle }) {
  return (
    <div className="grid gap-5">
      <div>
        <p className="hw-eyebrow">Source report</p>
        <p className="mt-2 font-serif text-lg leading-relaxed text-deep">{article.standfirst}</p>
      </div>
      <div>
        <p className="hw-eyebrow">Detected plants and entities</p>
        <ul className="mt-2 list-disc pl-5 font-sans text-sm leading-relaxed text-muted">
          {article.detected_entities.map((entity, index) => (
            <li key={`${entity.label}-${index}`}>
              {entity.label ?? "Unresolved entity"}
              {entity.ambiguous ? " — identity requires review" : ""}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="hw-eyebrow">Traceable evidence</p>
        <ul className="mt-2 grid gap-2 font-sans text-sm leading-relaxed text-muted">
          {(article.evidence_package.excerpts ?? []).map((excerpt, index) => (
            <li key={index} className="border-l-2 border-sage pl-3">
              {excerpt.text} <span className="text-xs">({excerpt.location})</span>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="hw-eyebrow">Limitations and safety</p>
        <ul className="mt-2 list-disc pl-5 font-sans text-sm leading-relaxed text-muted">
          {article.limitations.map((item) => <li key={item}>{item}</li>)}
        </ul>
        <p className="mt-3 font-sans text-sm leading-relaxed text-muted">{article.safety_context}</p>
      </div>
      <div>
        <p className="hw-eyebrow">What cannot be concluded</p>
        <ul className="mt-2 list-disc pl-5 font-sans text-sm leading-relaxed text-muted">
          {article.cannot_conclude.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>
      <div>
        <p className="hw-eyebrow">Provenance</p>
        <ul className="mt-2 grid gap-2 font-sans text-sm">
          {article.sources.map((source) => (
            <li key={source.id}>
              <a className="text-leaf underline" href={source.canonical_url} target="_blank" rel="noreferrer">
                {source.title}
              </a>
              <span className="block text-xs text-muted">
                PMID {source.pmid}{source.doi ? ` · DOI ${source.doi}` : ""}
                {source.journal ? ` · ${source.journal}` : ""}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export function DiscoveryReviewQueue() {
  const data = useAsyncResource(
    useCallback((signal: AbortSignal) => fetchDiscoveryReviews(signal), []),
  )
  const articles = useMemo(() => data.data?.items ?? [], [data.data])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const pageSize = 6
  const pageCount = Math.max(1, Math.ceil(articles.length / pageSize))
  const safePage = Math.min(page, pageCount)
  const pageArticles = useMemo(
    () => articles.slice((safePage - 1) * pageSize, safePage * pageSize),
    [articles, safePage],
  )
  const [reason, setReason] = useState("Needs additional evidence review.")
  const [message, setMessage] = useState("")
  const selected = useMemo(
    () => pageArticles.find((item) => item.id === selectedId) ?? pageArticles[0] ?? null,
    [pageArticles, selectedId],
  )

  async function decide(action: "approve" | "hold" | "reject") {
    if (!selected) return
    try {
      await decideDiscovery(selected.id, action, action === "approve" ? undefined : reason)
      setMessage(
        action === "approve"
          ? "Draft approved for a future publisher step; it remains non-public."
          : `Draft ${action === "hold" ? "held" : "rejected"} and remains non-public.`,
      )
      data.reload()
    } catch {
      setMessage("The editorial decision could not be saved.")
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Editorial / PubMed discovery"
        title="Discovery Review"
        description="Source-led drafts stop here for explicit human judgment. Milestone 4A cannot publish them."
        action={<button type="button" onClick={data.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Refresh</button>}
      />
      {data.isLoading ? <AdminStateCard title="Loading discovery drafts" description="Loading review-ready and held PubMed drafts." /> : null}
      {data.error ? <AdminStateCard title="Discovery queue unavailable" description="The authenticated review queue could not be loaded." action={<button type="button" onClick={data.reload}>Try again</button>} /> : null}
      {data.data && !articles.length ? <AdminStateCard title="No discovery drafts" description="Run one bounded PubMed collection from Pipeline Runs when a review window is ready." /> : null}
      {selected ? (
        <section aria-label="Discovery review workspace" className="grid gap-5 lg:grid-cols-[.7fr_1.3fr]">
          <Panel eyebrow="Private queue" title="Review drafts">
            <div className="grid gap-3">
              {pageArticles.map((article) => (
                <button
                  key={article.id}
                  type="button"
                  aria-pressed={selected.id === article.id}
                  onClick={() => setSelectedId(article.id)}
                  className={"border p-4 text-left " + (selected.id === article.id ? "border-leaf bg-sage/25" : "border-line")}
                >
                  <AdminStatusPill>{article.review_status ?? article.status}</AdminStatusPill>
                  <h2 className="mt-3 font-serif text-xl font-semibold text-deep">{article.headline}</h2>
                  <p className="mt-2 font-sans text-xs text-muted">{article.category}</p>
                </button>
              ))}
            </div>
            {articles.length ? (
              <div className="mt-5 flex items-center justify-between border-t border-line pt-4">
                <button type="button" aria-label="Previous discovery page" disabled={safePage === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button>
                <span className="font-sans text-xs text-muted">Page {safePage} of {pageCount}</span>
                <button type="button" aria-label="Next discovery page" disabled={safePage === pageCount} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>Next</button>
              </div>
            ) : null}
          </Panel>
          <Panel eyebrow="Draft detail" title={selected.headline}>
            <EvidenceView article={selected} />
            {message ? <p role="alert" className="mt-4 bg-gold/10 p-3 font-sans text-sm">{message}</p> : null}
            <div className="mt-5 border-t border-line pt-4">
              <label className="grid gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">
                Hold or reject reason
                <input value={reason} onChange={(event) => setReason(event.target.value)} className="min-h-11 border border-line bg-paper px-3 font-sans text-sm font-normal normal-case tracking-normal" />
              </label>
              <div className="mt-3 flex flex-wrap gap-3">
                <button type="button" onClick={() => decide("approve")} disabled={selected.status === "approved"} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">Approve</button>
                <button type="button" onClick={() => decide("hold")} className="border border-rust px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-rust">Hold</button>
                <button type="button" onClick={() => decide("reject")} className="bg-rust px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Reject</button>
              </div>
            </div>
          </Panel>
        </section>
      ) : null}
    </>
  )
}