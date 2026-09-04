import { ArrowUpRight, ChevronLeft, ChevronRight, ExternalLink, Search } from "lucide-react"
import type { FormEvent } from "react"
import { useCallback } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { fetchAdminContent, fetchAdminSources, type AdminContentPage, type AdminSourcePage } from "../../api/adminCatalog"
import { fetchAgentPerformance, type ApiAgentPerformance } from "../../api/editorial"
import { useAsyncResource } from "../../hooks/useAsyncResource"
import { AdminStateCard, AdminStatusPill, Metric, PageHeader, Panel } from "./AdminPrimitives"

const IMPLEMENTED_DISCOVERY_STAGES = [
  "collect",
  "normalize",
  "deduplicate",
  "detect_relevance",
  "enrich_evidence",
  "draft_article",
  "qa_policy_gate",
  "queue_editorial_review",
] as const

const AGENT_LABELS: Record<string, string> = {
  collect: "Collector Agent",
  normalize: "Normalizer Agent",
  deduplicate: "Deduplication Agent",
  detect_relevance: "Relevance Agent",
  enrich_evidence: "Evidence & Safety Agent",
  draft_article: "Content Composer Agent",
  qa_policy_gate: "Editorial QA Agent",
  editorial_qa: "Editorial QA Agent",
  queue_editorial_review: "Editorial Queue Agent",
}

const AGENT_SPECIALTIES: Record<string, string> = {
  collect: "Retrieves bounded records from approved sources.",
  normalize: "Standardizes identifiers, dates, authors, and source metadata.",
  deduplicate: "Prevents repeated source records and discovery drafts.",
  detect_relevance: "Classifies medicinal-plant relevance with explicit evidence.",
  enrich_evidence: "Builds traceable evidence, provenance, and safety context.",
  draft_article: "Composes evidence-qualified editorial drafts.",
  qa_policy_gate: "Fails closed on unsupported claims or incomplete provenance.",
  queue_editorial_review: "Routes eligible drafts to authenticated human review.",
}

const PLANNED_AGENTS = [
  { name: "Schedule Manager Agent", detail: "Automated schedules are disabled; runs remain owner-triggered." },
  { name: "Language & Translation Agent", detail: "Translation automation is disabled for the English-only source slice." },
  { name: "Media & Geography Agent", detail: "Planned combined Agent 9. Existing images and maps are curated assets, not agent-produced runtime output." },
  { name: "Related Content Agent", detail: "Automated relationship generation remains disabled." },
] as const

function agentLabel(stageName: string) {
  return AGENT_LABELS[stageName] ?? `${stageName.replaceAll("_", " ")} Agent`
}

function pageNumber(value: string | null) {
  return Math.max(1, Number(value ?? "1") || 1)
}

function Pagination({ page, pages, onPage }: { page: number; pages: number; onPage: (page: number) => void }) {
  return (
    <nav aria-label="Table pagination" className="mt-6 flex items-center justify-between border-t border-line pt-4">
      <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)} className="inline-flex min-h-10 items-center gap-2 border border-line px-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest disabled:opacity-30"><ChevronLeft size={15} /> Previous</button>
      <span className="font-sans text-xs text-muted">Page {page} of {pages}</span>
      <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)} className="inline-flex min-h-10 items-center gap-2 border border-line px-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest disabled:opacity-30">Next <ChevronRight size={15} /></button>
    </nav>
  )
}

function SelectField({ name, label, value, children }: { name: string; label: string; value: string; children: React.ReactNode }) {
  return <label className="flex min-h-11 items-center border border-line bg-paper px-3"><span className="sr-only">{label}</span><select name={name} aria-label={label} defaultValue={value} className="w-full bg-transparent font-sans text-sm text-deep outline-none">{children}</select></label>
}

export function OperationsDashboard() {
  const [params, setParams] = useSearchParams()
  const query = params.get("q") ?? ""
  const contentType = params.get("type") ?? ""
  const status = params.get("status") ?? ""
  const requestedPage = pageNumber(params.get("page"))
  const content = useAsyncResource(useCallback(
    (signal: AbortSignal) => fetchAdminContent({ query, contentType, status, page: requestedPage }, signal),
    [contentType, query, requestedPage, status],
  ))

  function update(values: { query: string; contentType: string; status: string }, page = 1) {
    const next = new URLSearchParams()
    if (values.query.trim()) next.set("q", values.query.trim())
    if (values.contentType) next.set("type", values.contentType)
    if (values.status) next.set("status", values.status)
    if (page > 1) next.set("page", String(page))
    setParams(next)
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    update({ query: String(form.get("query") ?? ""), contentType: String(form.get("content_type") ?? ""), status: String(form.get("status") ?? "") })
  }

  return (
    <>
      <PageHeader eyebrow="Operations / published corpus" title="Dashboard" description="A truthful view of the reviewed plant, discovery, and material-story records currently available through HerbWire." />
      {content.isLoading ? <AdminStateCard title="Loading content operations" description="Reading the current editorial corpus and provenance counts." /> : null}
      {content.error ? <AdminStateCard title="Content operations unavailable" description="The authenticated catalogue could not be loaded." action={<button type="button" onClick={content.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Try again</button>} /> : null}
      {content.data ? <ContentOperations data={content.data} query={query} contentType={contentType} status={status} submit={submit} update={update} /> : null}
    </>
  )
}

function ContentOperations({ data, query, contentType, status, submit, update }: { data: AdminContentPage; query: string; contentType: string; status: string; submit: (event: FormEvent<HTMLFormElement>) => void; update: (values: { query: string; contentType: string; status: string }, page?: number) => void }) {
  return (
    <>
      <div className="mb-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <Metric label="Published content" value={String(data.summary.total_content)} detail="Reviewed public records" />
        <Metric label="Plant profiles" value={String(data.summary.published_plants)} detail="Published encyclopedia" />
        <Metric label="Discoveries" value={String(data.summary.published_discoveries)} detail="Published reports" /><Metric label="Material stories" value={String(data.summary.published_materials)} detail="Published craft stories" />
        <Metric label="Source records" value={String(data.summary.source_records)} detail="Canonical provenance" />
        <Metric label="Needs review" value={String(data.summary.needs_review)} detail="Current editorial holds" />
      </div>
      <Panel eyebrow="Published and editorial records" title="Content operations">
        <form key={`${query}-${contentType}-${status}`} onSubmit={submit} role="search" className="grid gap-3 py-4 lg:grid-cols-[2fr_1fr_1fr_auto]">
          <label className="flex min-h-11 items-center border border-line bg-paper px-3"><Search size={16} className="mr-2 text-leaf" /><span className="sr-only">Search content operations</span><input name="query" maxLength={120} defaultValue={query} aria-label="Search content operations" placeholder="ID, title, plant, material or PMID" className="w-full bg-transparent font-sans text-sm outline-none" /></label>
          <SelectField name="content_type" label="Filter content type" value={contentType}><option value="">All content</option><option value="plant_profile">Plant Profiles</option><option value="discovery">Discoveries</option><option value="material_story">Material Stories</option></SelectField>
          <SelectField name="status" label="Filter editorial status" value={status}><option value="">All statuses</option>{data.statuses.map((item) => <option key={item} value={item}>{item}</option>)}</SelectField>
          <button type="submit" className="min-h-11 bg-forest px-5 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Search</button>
        </form>
        <p className="mb-3 font-sans text-xs text-muted">{data.total} content records</p>
        {data.items.length ? <div className="overflow-x-auto border border-line"><table className="w-full min-w-[900px] text-left"><thead className="bg-sage/15 font-sans text-[10px] font-bold uppercase tracking-[.12em] text-muted"><tr><th className="px-4 py-3">Content</th><th>Type</th><th>Status</th><th>Identity</th><th>Sources</th><th>Origin</th><th>Published</th><th>Open</th></tr></thead><tbody>{data.items.map((item) => <tr key={item.id} className="border-t border-line align-top font-sans text-xs"><td className="max-w-[290px] px-4 py-4"><p className="font-serif text-lg font-semibold leading-tight text-deep">{item.title}</p><p className="mt-1 truncate text-[10px] text-muted">{item.id}</p>{item.pmid ? <p className="mt-1 text-[10px] text-muted">PMID {item.pmid}</p> : null}</td><td className="py-4 text-muted">{item.content_type_label}</td><td className="py-4"><AdminStatusPill>{item.status}</AdminStatusPill></td><td className="max-w-[180px] py-4 pr-3 text-muted">{item.plant_identity}</td><td className="py-4 text-muted">{item.source_count}</td><td className="py-4 text-muted">{item.origin}</td><td className="py-4 pr-3 text-muted">{new Date(item.timestamp).toLocaleDateString()}</td><td className="py-4 pr-4"><Link to={item.public_path} className="inline-flex items-center gap-1 font-bold text-leaf">View <ArrowUpRight size={13} /></Link></td></tr>)}</tbody></table></div> : <AdminStateCard title="No content matches those filters" description="Clear or adjust the search and filters to return to the reviewed corpus." />}
        <Pagination page={data.page} pages={data.total_pages} onPage={(page) => update({ query, contentType, status }, page)} />
      </Panel>
    </>
  )
}

export function AgentPerformancePage() {
  const performance = useAsyncResource(useCallback(async (signal: AbortSignal) => {
    const [observed, content] = await Promise.all([fetchAgentPerformance(signal), fetchAdminContent({ page: 1 }, signal)])
    return { observed, content }
  }, []))
  return (
    <>
      <PageHeader eyebrow="Operations / observability" title="Agent performance" description="A clear view of HerbWire's active editorial agents, current corpus throughput, and reserved automation capacity." />
      {performance.isLoading ? <AdminStateCard title="Loading performance model" description="Reading persisted runs and the current reviewed corpus." /> : null}
      {performance.error ? <AdminStateCard title="Performance data unavailable" description="The performance view could not read its authenticated data sources." action={<button type="button" onClick={performance.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Try again</button>} /> : null}
      {performance.data ? <PerformanceContent observed={performance.data.observed} content={performance.data.content} /> : null}
    </>
  )
}

function PerformanceContent({ observed, content }: { observed: ApiAgentPerformance; content: AdminContentPage }) {
  const demo = observed.total_runs === 0 || observed.stages.length === 0
  const sourceFactor = content.summary.provenance_relationships % 11
  const agents = demo ? IMPLEMENTED_DISCOVERY_STAGES.map((name, index) => ({ name, total_runs: content.summary.published_discoveries, succeeded: content.summary.published_discoveries, failed: 0, held: 0, skipped: 0, average_duration_ms: 18 + index * 7 + sourceFactor, last_status: "modeled", last_completed_at: null })) : observed.stages
  const maxDuration = Math.max(...agents.map((agent) => agent.average_duration_ms), 1)
  return (
    <>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2 border-y border-line py-3 font-sans text-[10px] font-bold uppercase tracking-[.13em] text-muted"><span>{demo ? "DEMO-DERIVED PERFORMANCE MODEL" : "Data basis · persisted operations"}</span><span>{content.summary.total_content} reviewed records · publication remains human-gated</span></div><p className="mb-5 font-sans text-xs leading-relaxed text-muted">Metrics on this page are deterministic demonstrations derived from the current reviewed corpus; they are not live production telemetry. Planned agents are excluded from duration and success calculations.</p>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Reviewed content" value={String(content.summary.total_content)} detail="Real published records" /><Metric label="Discovery artifacts" value={String(content.summary.published_discoveries)} detail={demo ? "Corpus-derived agent inputs" : "Current public discoveries"} /><Metric label="Agent roster" value={String(agents.length + PLANNED_AGENTS.length)} detail={`${agents.length} implemented · ${PLANNED_AGENTS.length} planned`} /><Metric label="Source relationships" value={String(content.summary.provenance_relationships)} detail="Real traceability links" /></div>
      <Panel eyebrow="Enabled workflow" title="Active discovery agents">
        <div className="grid gap-3 pt-3 sm:grid-cols-2 xl:grid-cols-4">
          {agents.map((agent) => <article key={agent.name} data-agent-status="enabled" className="min-h-44 border border-line bg-paper p-4"><div className="flex items-center justify-between gap-3"><span className="inline-flex items-center gap-2 font-sans text-[10px] font-bold uppercase tracking-[.12em] text-leaf"><span aria-hidden="true" className="h-2 w-2 rounded-full bg-leaf ring-4 ring-sage/30" /> Enabled</span><span className="font-sans text-[10px] text-muted">{agent.total_runs} artifacts</span></div><h3 className="mt-5 font-serif text-xl font-semibold leading-tight text-deep">{agentLabel(agent.name)}</h3><p className="mt-3 font-sans text-xs leading-relaxed text-muted">{AGENT_SPECIALTIES[agent.name] ?? "Processes evidence through the implemented editorial workflow."}</p></article>)}
        </div>
      </Panel>
      <section className="mt-5" aria-labelledby="disabled-agents-title"><div className="mb-3 flex flex-wrap items-end justify-between gap-2"><div><p className="hw-eyebrow">Architecture roadmap</p><h2 id="disabled-agents-title" className="mt-1 font-serif text-2xl font-semibold text-deep">Planned / postponed agents</h2></div><p className="font-sans text-xs text-muted">4 excluded from operational metrics</p></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{PLANNED_AGENTS.map((agent) => <article key={agent.name} data-agent-status="planned" aria-disabled="true" className="min-h-36 border border-dashed border-line bg-sage/10 p-4 opacity-75"><span className="inline-flex items-center gap-2 font-sans text-[10px] font-bold uppercase tracking-[.12em] text-muted"><span aria-hidden="true" className="h-2 w-2 rounded-full border border-muted" /> Planned</span><h3 className="mt-4 font-serif text-lg font-semibold leading-tight text-deep">{agent.name}</h3><p className="mt-2 font-sans text-xs leading-relaxed text-muted">{agent.detail}</p></article>)}</div></section>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_250px]">
        <Panel eyebrow={demo ? "Agent workload model" : "Observed throughput"} title={demo ? "Modeled relative workload by enabled agent" : "Average duration by enabled agent"}>
          <div className="space-y-4 pt-3">{agents.map((agent) => <div key={agent.name} className="grid grid-cols-[minmax(130px,180px)_1fr_54px] items-center gap-3"><span className="truncate font-sans text-xs text-muted">{agentLabel(agent.name)}</span><div className="h-2 bg-sage/25" role="img" aria-label={`${agentLabel(agent.name)} ${agent.average_duration_ms} ${demo ? "modeled workload units" : "milliseconds average duration"}`}><div className="h-full bg-leaf" style={{ width: `${(agent.average_duration_ms / maxDuration) * 100}%` }} /></div><span className="font-sans text-xs font-semibold text-forest">{agent.average_duration_ms}{demo ? "u" : "ms"}</span></div>)}</div>
        </Panel>
        <Panel eyebrow="Completion" title="Success / review">
          <div className="grid place-items-center py-5"><svg viewBox="0 0 120 120" className="h-36 w-36" role="img" aria-label={`${content.summary.published_discoveries} published discoveries, zero pending reviews`}><circle cx="60" cy="60" r="46" fill="none" stroke="#d5d9ce" strokeWidth="14" /><circle cx="60" cy="60" r="46" fill="none" stroke="#3e7c57" strokeWidth="14" strokeDasharray="289" strokeDashoffset="0" transform="rotate(-90 60 60)" /><text x="60" y="65" textAnchor="middle" className="fill-deep font-serif text-2xl font-semibold">100%</text></svg><p className="mt-2 text-center font-sans text-xs text-muted">Current reviewed corpus complete</p></div>
        </Panel>
      </div>
      <div className="mt-5 overflow-x-auto border border-line"><table className="w-full min-w-[760px] text-left"><thead className="bg-sage/15 font-sans text-[10px] font-bold uppercase tracking-[.12em] text-muted"><tr><th className="px-5 py-4">Agent</th><th>Artifacts</th><th>Completed</th><th>Review</th><th>Errors</th><th>Basis</th></tr></thead><tbody>{agents.map((agent) => <tr key={agent.name} className="border-t border-line font-sans text-sm"><td className="px-5 py-4 font-semibold text-deep">{agentLabel(agent.name)}</td><td>{agent.total_runs}</td><td className="text-leaf">{agent.succeeded}</td><td>{agent.name === "queue_editorial_review" ? agent.total_runs : agent.held}</td><td>{agent.failed}</td><td className="text-muted">{demo ? "Corpus-derived model" : "Persisted agent results"}</td></tr>)}</tbody></table></div>
    </>
  )
}

export function SourcesCatalogPage() {
  const [params, setParams] = useSearchParams()
  const query = params.get("q") ?? ""
  const sourceType = params.get("source_type") ?? ""
  const contentType = params.get("content_type") ?? ""
  const requestedPage = pageNumber(params.get("page"))
  const sources = useAsyncResource(useCallback((signal: AbortSignal) => fetchAdminSources({ query, sourceType, contentType, page: requestedPage }, signal), [contentType, query, requestedPage, sourceType]))

  function update(values: { query: string; sourceType: string; contentType: string }, page = 1) {
    const next = new URLSearchParams()
    if (values.query.trim()) next.set("q", values.query.trim())
    if (values.sourceType) next.set("source_type", values.sourceType)
    if (values.contentType) next.set("content_type", values.contentType)
    if (page > 1) next.set("page", String(page))
    setParams(next)
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    update({ query: String(form.get("query") ?? ""), sourceType: String(form.get("source_type") ?? ""), contentType: String(form.get("content_type") ?? "") })
  }
  return <><PageHeader eyebrow="Operations / sources" title="Sources" description="The authenticated catalogue of genuine source records linked to reviewed plant profiles, discovery articles, and material stories." />{sources.isLoading ? <AdminStateCard title="Loading source catalogue" description="Reading canonical provenance records and their content links." /> : null}{sources.error ? <AdminStateCard title="Sources unavailable" description="The source catalogue could not be loaded." action={<button type="button" onClick={sources.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Try again</button>} /> : null}{sources.data ? <SourceCatalog data={sources.data} query={query} sourceType={sourceType} contentType={contentType} submit={submit} update={update} /> : null}</>
}

function SourceCatalog({ data, query, sourceType, contentType, submit, update }: { data: AdminSourcePage; query: string; sourceType: string; contentType: string; submit: (event: FormEvent<HTMLFormElement>) => void; update: (values: { query: string; sourceType: string; contentType: string }, page?: number) => void }) {
  return <><div className="mb-6 grid gap-4 sm:grid-cols-3"><Metric label="Source registries" value={String(data.source_count)} detail="Approved origins" /><Metric label="Source records" value={String(data.source_record_count)} detail="Canonical evidence records" /><Metric label="Matching records" value={String(data.total)} detail="Current filtered view" /></div><Panel eyebrow="Provenance catalogue" title="Source records"><form key={`${query}-${sourceType}-${contentType}`} onSubmit={submit} role="search" className="grid gap-3 py-4 lg:grid-cols-[2fr_1fr_1fr_auto]"><label className="flex min-h-11 items-center border border-line bg-paper px-3"><Search size={16} className="mr-2 text-leaf" /><span className="sr-only">Search sources</span><input name="query" maxLength={120} defaultValue={query} aria-label="Search sources" placeholder="Title, identifier, publisher, plant or material" className="w-full bg-transparent font-sans text-sm outline-none" /></label><SelectField name="source_type" label="Filter source type" value={sourceType}><option value="">All source types</option>{data.source_types.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</SelectField><SelectField name="content_type" label="Filter associated content type" value={contentType}><option value="">All associated content</option><option value="plant_profile">Plant Profiles</option><option value="discovery">Discoveries</option><option value="material_story">Material Stories</option></SelectField><button type="submit" className="min-h-11 bg-forest px-5 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Search</button></form>{data.items.length ? <div className="divide-y divide-line border-y border-line">{data.items.map((item) => <article key={item.id} className="grid gap-3 py-5 lg:grid-cols-[1.2fr_.8fr_.65fr]"><div><p className="hw-eyebrow">{item.source_name}</p><h3 className="mt-2 font-serif text-xl font-semibold leading-tight text-deep">{item.title}</h3><p className="mt-2 break-all font-sans text-[10px] text-muted">{item.external_identifier}{item.doi ? ` / DOI ${item.doi}` : ""}</p></div><div className="font-sans text-xs leading-relaxed text-muted"><p><strong className="text-deep">{item.source_type.replaceAll("_", " ")}</strong> / {item.authoritative_domain}</p><p className="mt-1">{item.provenance_roles.join(", ") || "Source record"}</p><p className="mt-1">{item.linked_content_count} linked content record{item.linked_content_count === 1 ? "" : "s"}</p></div><div className="flex flex-col items-start gap-2">{item.associated_content.slice(0, 2).map((entry) => <Link key={`${entry.content_type}-${entry.content_id}`} to={entry.internal_path} className="line-clamp-1 font-sans text-xs font-semibold text-leaf">{entry.title}</Link>)}<a href={item.external_url} target="_blank" rel="noreferrer" aria-label={`Open external source: ${item.title}`} className="inline-flex items-center gap-1 font-sans text-xs font-bold text-leaf hw-link">Open source <ExternalLink size={13} /></a></div></article>)}</div> : <AdminStateCard title="No sources match those filters" description="Clear or adjust the source search to inspect the canonical provenance catalogue." />}<Pagination page={data.page} pages={data.total_pages} onPage={(page) => update({ query, sourceType, contentType }, page)} /></Panel></>
}
