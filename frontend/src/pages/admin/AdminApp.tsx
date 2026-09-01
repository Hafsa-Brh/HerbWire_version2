import { Activity, Database, Eye, Filter, GitCompareArrows, LayoutDashboard, LogOut, Menu, Search, ShieldCheck, Sprout, Workflow, X, Zap } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { Link, Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom"
import { fetchSession, logout } from "../../api/auth"
import { approvePlantRevision, approveReview, fetchAgentPerformance, fetchPipelineRuns, fetchPlantRevisions, fetchReviews, holdPlantRevision, promotePlantRevision, publishPlant, rejectReview, type ApiAgentPerformance, type ApiPipelineRun, type ApiPlantRevision, type ApiReview } from "../../api/editorial"
import { ApiRequestError, fetchPlants, type ApiPlantDetail, type ApiPlantListItem } from "../../api/plants"
import { BotanicalImage, PlantDistributionMap } from "../../components/plants/PlantPrimitives"
import { useAsyncResource } from "../../hooks/useAsyncResource"
import { AdminStateCard, AdminStatusPill, Metric, PageHeader, Panel } from "./AdminPrimitives"

type AdminData = { reviews: ApiReview[]; runs: ApiPipelineRun[] }
type NavItem = { label: string; path: string; icon: typeof Activity }

const navItems: readonly NavItem[] = [
  { label: "Dashboard", path: "/admin", icon: LayoutDashboard },
  { label: "Review Queue", path: "/admin/reviews", icon: ShieldCheck },
  { label: "Profile Revisions", path: "/admin/revisions", icon: GitCompareArrows },
  { label: "Flashes", path: "/admin/flashes", icon: Zap },
  { label: "Agent Performance", path: "/admin/agents", icon: Activity },
  { label: "Pipeline Runs", path: "/admin/runs", icon: Workflow },
  { label: "Sources", path: "/admin/sources", icon: Database },
]

function AdminLogo({ inverse = false }: { inverse?: boolean }) {
  return <Link to="/" className="flex items-center gap-2.5" aria-label="HerbWire home"><span className={`grid h-9 w-9 place-items-center rounded-full ${inverse ? "bg-sage/20 text-sage" : "bg-forest text-sage"}`}><Sprout size={18} /></span><span className={`font-serif text-xl font-semibold tracking-[-.04em] ${inverse ? "text-cream" : "text-deep"}`}>Herb<span className="text-leaf">Wire</span></span></Link>
}

export function AdminApp() {
  const session = useAsyncResource(useCallback((signal: AbortSignal) => fetchSession(signal), []))

  if (session.isLoading) return <div className="min-h-screen bg-paper p-6"><AdminStateCard title="Checking editorial session" description="Confirming backend-authenticated local access." /></div>
  if (session.error || !session.data?.authenticated) return <Navigate to="/login" replace />

  return <AdminShell user={session.data.user ?? { initials: "HB", label: "Local admin", role: "Milestone 2 editor" }} />
}

function AdminShell({ user }: { user: { initials: string; label: string; role: string } }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  async function signOut() {
    await logout().catch(() => undefined)
    navigate("/login", { replace: true })
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 border-b border-line bg-paper/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1320px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <button className="grid h-9 w-9 place-items-center text-forest md:hidden" onClick={() => setOpen(!open)} aria-label="Toggle admin navigation">{open ? <X size={19} /> : <Menu size={19} />}</button>
          <AdminLogo />
          <div className="hidden items-center gap-3 sm:flex"><Link to="/" className="inline-flex items-center gap-2 border border-line px-3 py-2 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-muted hover:border-leaf hover:text-leaf"><Eye size={14} /> View public site</Link></div>
        </div>
      </header>
      <div className="mx-auto flex max-w-[1320px] items-start px-4 sm:px-6 lg:px-8">
        <aside className={`${open ? "fixed inset-x-4 top-20 z-20 block shadow-xl" : "hidden"} w-64 shrink-0 border border-line bg-paper md:fixed md:bottom-8 md:left-[max(1.5rem,calc((100vw-1320px)/2+1.5rem))] md:top-24 md:block md:overflow-y-auto md:border-0 md:bg-transparent md:py-0 md:shadow-none`}>
          <div className="flex min-h-full flex-col p-4 md:p-0">
            <p className="hw-eyebrow mb-4">Editorial desk</p>
            <nav className="grid gap-1" aria-label="Editorial navigation">{navItems.map((item) => { const Icon = item.icon; return <NavLink key={item.path} to={item.path} end={item.path === "/admin"} onClick={() => setOpen(false)} className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 font-sans text-sm ${isActive ? "bg-sage/35 font-semibold text-forest" : "text-muted hover:bg-sage/15 hover:text-forest"}`}><Icon size={16} />{item.label}</NavLink> })}</nav>
            <div className="my-6 border-t border-line" />
            <p className="mb-3 px-3 font-sans text-[10px] font-bold uppercase tracking-[.14em] text-muted">System</p>
            <div className="grid gap-1 px-3 py-2 font-sans text-xs text-muted"><div className="flex items-center gap-3"><SettingsDot /><span>Backend session</span><span className="ml-auto h-1.5 w-1.5 rounded-full bg-leaf" /></div><span className="pl-6 text-[10px] leading-relaxed text-muted">HttpOnly local admin cookie. No browser-bundled secret.</span></div>
            <div className="mt-8 border-t border-line pt-5">
              <div className="flex items-center gap-3 px-3">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-deep font-serif text-sm text-cream">{user.initials}</span>
                <div className="min-w-0 flex-1"><p className="font-sans text-xs font-semibold text-forest">{user.label}</p><p className="font-sans text-[10px] text-muted">{user.role}</p></div>
              </div>
              <button type="button" onClick={signOut} className="mt-4 flex w-full items-center gap-3 px-3 py-2.5 font-sans text-sm text-muted hover:bg-sage/15 hover:text-rust"><LogOut size={16} />Logout</button>
            </div>
          </div>
        </aside>
        <main className="min-w-0 flex-1 py-7 md:ml-[19rem] md:py-10">
          <Routes>
            <Route index element={<Dashboard />} />
            <Route path="reviews" element={<ReviewQueue />} />
            <Route path="revisions" element={<ProfileRevisions />} />
            <Route path="review" element={<Navigate to="/admin/reviews" replace />} />
            <Route path="flashes" element={<Flashes />} />
            <Route path="agents" element={<AgentPerformance />} />
            <Route path="runs" element={<PipelineRuns />} />
            <Route path="sources" element={<Sources />} />
            <Route path="*" element={<AdminStateCard title="Admin page not found" description="That editorial route does not exist. Use the navigation to return to a live desk page." action={<Link to="/admin" className="inline-flex items-center gap-2 bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Return to dashboard</Link>} />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function SettingsDot() { return <span className="grid h-3.5 w-3.5 place-items-center rounded-full border border-leaf text-leaf"><span className="h-1.5 w-1.5 rounded-full bg-current" /></span> }

function useAdminData() {
  return useAsyncResource<AdminData>(useCallback(async (signal: AbortSignal) => ({
    reviews: await fetchReviews(signal),
    runs: [],
  }), []))
}
function Dashboard() {
  return <><PageHeader eyebrow="Operations / overview" title="Dashboard" description="This workspace is reserved for the scheduled collection, orchestration, and agent operations planned for the next approved milestone." /><AdminStateCard eyebrow="Future operations" title="No operational dashboard yet" description="Static encyclopedia review is available in Review Queue. Live collection health, schedules, agent activity, and orchestration metrics will appear here only after those systems are implemented." action={<Link to="/admin/reviews" className="inline-flex items-center gap-2 bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Open review queue</Link>} /></>
}
function ReviewQueue() {
  const data = useAdminData()
  const reviews = data.data?.reviews ?? []
  return <><PageHeader eyebrow="Editorial / review" title="Review Queue" description="Human judgment is the final publication gate. Drafts can be approved, held with a reason, and published only after approval." action={<button type="button" onClick={data.reload} className="inline-flex items-center gap-2 bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream hover:bg-leaf">Refresh</button>} />{data.data ? <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Review items" value={String(reviews.length)} detail="Profiles in the editorial queue" /><Metric label="Needs attention" value={String(reviews.filter((review) => review.status === "needs_review" || review.status === "held").length)} detail="Drafts or held items" /><Metric label="Approved" value={String(reviews.filter((review) => review.status === "approved").length)} detail="Ready for publication" /><Metric label="Published" value={String(reviews.filter((review) => review.plant_profile?.status === "published").length)} detail="Visible publicly" /></div> : null}{data.isLoading ? <AdminStateCard title="Loading review queue" description="Pulling the latest items waiting for human judgment." /> : null}{data.error ? <AdminStateCard title="Review queue unavailable" description="The editorial review queue could not be loaded right now." action={<button type="button" onClick={data.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Try again</button>} /> : null}{data.data ? <ReviewPanel data={data.data} /> : null}</>
}
const REVIEW_SECTIONS = [
  { id: "overview", title: "Overview" },
  { id: "botanical", title: "Botanical content" },
  { id: "traditional", title: "Traditional use & preparation" },
  { id: "safety", title: "Safety & evidence" },
  { id: "distribution", title: "Distribution & sources" },
] as const

type ReviewSectionId = (typeof REVIEW_SECTIONS)[number]["id"]
type ReviewablePlant = ApiPlantDetail | ApiPlantRevision["proposed_content"]

function ReviewPanel({ data }: { data: AdminData }) {
  const pageSize = 6
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [reason, setReason] = useState("Needs additional source review.")
  const [message, setMessage] = useState("")
  const [filter, setFilter] = useState("all")
  const [page, setPage] = useState(1)
  const filteredReviews = useMemo(() => data.reviews.filter((review) => {
    const plant = review.plant_profile
    if (filter === "all") return true
    if (filter === "ready_for_review") return plant?.readiness_status === "ready_for_review" && review.status === "needs_review"
    if (filter === "missing_image") return !plant?.hero_image.local_path
    if (filter === "missing_safety") return !plant?.safety_notes.length
    if (filter === "missing_distribution") return !plant?.distribution.length
    if (filter === "approved") return review.status === "approved"
    if (filter === "published") return plant?.status === "published"
    if (filter === "held") return review.status === "held" || plant?.readiness_status === "held"
    return true
  }), [data.reviews, filter])
  const pageCount = Math.max(1, Math.ceil(filteredReviews.length / pageSize))
  const safePage = Math.min(page, pageCount)
  const pageReviews = useMemo(() => filteredReviews.slice((safePage - 1) * pageSize, safePage * pageSize), [filteredReviews, safePage])
  const selected = useMemo(() => pageReviews.find((review) => review.id === selectedId) ?? pageReviews[0] ?? null, [pageReviews, selectedId])

  function approveSelected() { if (selected) approveReview(selected.id).then(() => setMessage("Review approved. Refresh to see updated state.")).catch(() => setMessage("Approval failed.")) }
  function holdSelected() { if (selected) rejectReview(selected.id, reason).then(() => setMessage("Review placed on hold. Refresh to see updated state.")).catch(() => setMessage("Hold failed.")) }
  function publishSelected() { if (selected?.plant_profile) publishPlant(selected.plant_profile.id).then(() => setMessage("Profile published to the public encyclopedia. Refresh to see updated state.")).catch(() => setMessage("Publication requires an approved, complete plant profile with provenance, licensed media, distribution, and safety notes.")) }

  return <section aria-label="Review workspace" className="grid items-stretch gap-5 lg:grid-cols-[.75fr_1.25fr]">
    <Panel eyebrow="Needs attention" title="Review queue" className="h-full">
      <label className="mb-4 grid gap-2 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest">Completeness filter
        <select aria-label="Completeness filter" value={filter} onChange={(event) => { setFilter(event.target.value); setPage(1) }} className="min-h-10 border border-line bg-paper px-3 font-sans text-sm font-normal normal-case tracking-normal text-deep">
          <option value="all">All profiles</option><option value="ready_for_review">Ready for review</option><option value="missing_image">Missing image</option><option value="missing_safety">Missing safety evidence</option><option value="missing_distribution">Missing distribution</option><option value="approved">Approved</option><option value="published">Published</option><option value="held">Held</option>
        </select>
      </label>
      <div className="grid gap-3">{pageReviews.length ? pageReviews.map((review) => {
        const isSelected = selected?.id === review.id
        return <button key={review.id} type="button" aria-pressed={isSelected} onClick={() => setSelectedId(review.id)} className={"block border p-4 text-left " + (isSelected ? "border-leaf bg-sage/25" : "border-line bg-paper hover:border-leaf")}><div className="flex items-center justify-between gap-3"><AdminStatusPill>{review.status}</AdminStatusPill><span className="font-sans text-xs text-muted">{review.plant_profile?.readiness_status ?? "held"}</span></div><h2 className="mt-3 font-serif text-xl font-semibold text-deep">{review.plant_profile?.display_common_name ?? "Discovery item"}</h2><p className="mt-2 font-sans text-xs text-muted">{review.content_type}</p></button>
      }) : <p className="font-sans text-sm text-muted">No review items match this filter.</p>}</div>
      {filteredReviews.length ? <QueuePagination page={safePage} pageCount={pageCount} onPrevious={() => setPage((current) => Math.max(1, current - 1))} onNext={() => setPage((current) => Math.min(pageCount, current + 1))} /> : null}
    </Panel>
    <Panel eyebrow="Article review" title={selected?.plant_profile?.display_common_name ?? "Select a review item"} className="flex h-full min-w-0 flex-col">
      {selected?.plant_profile ? <PlantReviewPreview plant={selected.plant_profile} selectionKey={selected.id} /> : <p className="font-sans text-sm text-muted">No profile selected.</p>}
      {message ? <p role="alert" className="mt-4 border border-gold/40 bg-gold/10 p-3 font-sans text-sm text-deep">{message}</p> : null}
      <div className="mt-auto flex flex-wrap items-end gap-3 border-t border-line pt-4"><button type="button" onClick={approveSelected} disabled={!selected || selected.status === "approved" || selected.plant_profile?.readiness_status !== "ready_for_review"} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream hover:bg-leaf disabled:opacity-50">Approve</button><button type="button" onClick={publishSelected} disabled={!selected?.plant_profile || selected.status !== "approved" || selected.plant_profile.status === "published"} className="bg-leaf px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream hover:bg-forest disabled:opacity-50">Publish</button><label className="grid gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">Hold reason<input value={reason} onChange={(event) => setReason(event.target.value)} className="min-h-11 w-[min(25rem,70vw)] border border-line bg-paper px-3 font-sans text-sm font-normal normal-case tracking-normal text-deep outline-none focus:border-leaf" /></label><button type="button" onClick={holdSelected} disabled={!selected || selected.status === "approved"} className="border border-rust px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-rust hover:bg-rust hover:text-cream disabled:opacity-50">Hold / reject</button></div>
    </Panel>
  </section>
}

function QueuePagination({ page, pageCount, onPrevious, onNext }: { page: number; pageCount: number; onPrevious: () => void; onNext: () => void }) {
  return <div className="mt-5 flex items-center justify-between border-t border-line pt-4"><button type="button" aria-label="Previous queue page" onClick={onPrevious} disabled={page === 1} className="border border-line px-3 py-2 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest disabled:opacity-35">Previous</button><span className="font-sans text-xs text-muted">Page {page} of {pageCount}</span><button type="button" aria-label="Next queue page" onClick={onNext} disabled={page === pageCount} className="border border-line px-3 py-2 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest disabled:opacity-35">Next</button></div>
}

function ReviewSectionPager({ selectionKey, renderSection }: { selectionKey: string; renderSection: (section: ReviewSectionId) => ReactNode }) {
  const [sectionIndex, setSectionIndex] = useState(0)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const shouldFocus = useRef(false)
  const active = REVIEW_SECTIONS[sectionIndex]
  const titleId = `review-section-${selectionKey}`


  useEffect(() => {
    if (shouldFocus.current) {
      headingRef.current?.focus()
      shouldFocus.current = false
    }
  }, [sectionIndex])

  function goTo(nextIndex: number) {
    if (nextIndex === sectionIndex || nextIndex < 0 || nextIndex >= REVIEW_SECTIONS.length) return
    shouldFocus.current = true
    setSectionIndex(nextIndex)
  }

  return <div className="flex min-h-0 flex-1 flex-col">
    <div className="border-y border-line py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2"><h3 id={titleId} ref={headingRef} tabIndex={-1} className="font-serif text-2xl font-semibold text-deep outline-none">{active.title}</h3><p aria-live="polite" className="font-sans text-xs text-muted">Section {sectionIndex + 1} of {REVIEW_SECTIONS.length}</p></div>
      <nav aria-label="Article review sections" className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5">{REVIEW_SECTIONS.map((section, index) => <button key={section.id} type="button" aria-label={`Open ${section.title} section`} aria-current={index === sectionIndex ? "step" : undefined} onClick={() => goTo(index)} className={"min-h-10 border px-2 py-2 font-sans text-[10px] font-bold uppercase tracking-[.06em] " + (index === sectionIndex ? "border-forest bg-forest text-cream" : "border-line bg-paper text-muted hover:border-leaf hover:text-forest")}><span aria-hidden="true" className="mr-1">{index + 1}.</span>{section.title}</button>)}</nav>
    </div>
    <div role="region" aria-labelledby={titleId} className="min-h-0 py-4 lg:h-[30rem] lg:overflow-y-auto lg:pr-2">{renderSection(active.id)}</div>
    <div className="mt-auto flex items-center justify-between border-t border-line pt-3"><button type="button" aria-label="Previous review section" onClick={() => goTo(sectionIndex - 1)} disabled={sectionIndex === 0} className="border border-line px-3 py-2 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest disabled:opacity-35">Previous</button><span className="font-sans text-xs text-muted">{active.title}</span><button type="button" aria-label="Next review section" onClick={() => goTo(sectionIndex + 1)} disabled={sectionIndex === REVIEW_SECTIONS.length - 1} className="border border-line px-3 py-2 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest disabled:opacity-35">Next</button></div>
  </div>
}

function PlantReviewPreview({ plant, selectionKey }: { plant: ApiPlantDetail; selectionKey: string }) {
  return <ReviewSectionPager key={selectionKey} selectionKey={selectionKey} renderSection={(section) => <PlantReviewSection plant={plant} sources={plant.sources} section={section} status={plant.status} version={plant.version} />} />
}

function PlantReviewSection({ plant, sources, section, status, version }: { plant: ReviewablePlant; sources: ApiPlantDetail["sources"]; section: ReviewSectionId; status?: string; version: number }) {
  const informationSources = sources.filter((source) => source.source_type !== "licensed_media")
  const distributionPlant: ApiPlantDetail = { ...plant, id: "editorial-preview", slug: "editorial-preview", status: status ?? "revision", published_at: null, source_count: informationSources.length, version, last_reviewed_at: null, sources }
  const checks = [
    ["Sources", informationSources.length > 0],
    ["Licensed image", Boolean(plant.hero_image.local_path && plant.hero_image.license)],
    ["Safety evidence", plant.safety_notes.length > 0],
    ["Distribution", plant.distribution.length > 0],
  ] as const

  if (section === "overview") return <div>
    <div className="flex flex-wrap items-center gap-3">{status ? <AdminStatusPill>{status}</AdminStatusPill> : null}<AdminStatusPill>{plant.readiness_status}</AdminStatusPill><span className="font-sans text-xs text-muted">Version {version}</span></div>
    <h4 className="mt-4 font-serif text-3xl font-semibold tracking-[-.045em] text-deep">{plant.display_common_name}</h4><p className="mt-1 font-serif text-base italic text-muted">{plant.accepted_scientific_name} {plant.botanical_author}</p><p className="mt-1 font-sans text-xs uppercase tracking-[.08em] text-muted">{plant.family_name ?? "Family unavailable"}</p>
    <div className="mt-5 max-w-2xl"><BotanicalImage label={plant.display_common_name} image={plant.hero_image} /></div>
    <div className="mt-3 border-l-2 border-leaf pl-3 font-sans text-xs leading-relaxed text-muted"><strong className="text-deep">Media attribution:</strong> {plant.hero_image.attribution ?? "No licensed image attribution"}<span className="block">License: {plant.hero_image.license ?? "License missing"}{plant.hero_image.license_url ? <> / <a href={plant.hero_image.license_url} target="_blank" rel="noreferrer" className="font-bold text-leaf">license terms</a></> : null}</span></div>
    <p className="mt-5 font-serif text-lg leading-relaxed text-muted">{plant.summary}</p><p className="mt-3 font-serif text-lg leading-relaxed text-muted">{plant.introduction}</p>
  </div>

  if (section === "botanical") return <div className="grid gap-4 sm:grid-cols-2">
    <ReviewContentBlock title="Botanical identity"><p>{plant.botanical_description}</p><dl className="mt-4 grid gap-2 text-xs"><div><dt className="font-bold text-deep">Taxon identifier</dt><dd>{plant.taxon_identifier}</dd></div><div><dt className="font-bold text-deep">Known synonyms</dt><dd>{plant.known_synonyms.length ? plant.known_synonyms.join(", ") : "None recorded."}</dd></div></dl></ReviewContentBlock>
    <ReviewContentBlock title="Form and habitat"><dl className="grid gap-3"><div><dt className="font-bold text-deep">Growth form</dt><dd>{plant.growth_form || "Not recorded."}</dd></div><div><dt className="font-bold text-deep">Biome</dt><dd>{plant.biome || "Not recorded."}</dd></div><div><dt className="font-bold text-deep">Geographical / traditional context</dt><dd>{plant.diversity_tags.length ? plant.diversity_tags.join(", ") : "Not recorded."}</dd></div></dl></ReviewContentBlock>
    <ReviewContentBlock title="Parts traditionally used" className="sm:col-span-2"><ul className="list-disc pl-5">{plant.parts_used.length ? plant.parts_used.map((part) => <li key={part}>{part}</li>) : <li>Not recorded.</li>}</ul></ReviewContentBlock>
  </div>

  if (section === "traditional") return <div className="grid gap-4">
    <ReviewContentBlock title="Qualified traditional uses"><div className="grid gap-4">{plant.traditional_uses.length ? plant.traditional_uses.map((use) => <article key={use.tradition + use.statement}><p className="font-bold text-deep">{use.tradition}</p><p className="mt-1">{use.statement}</p><p className="mt-2 border-l-2 border-gold pl-3 text-xs">Qualification: {use.limitation}</p></article>) : <p>No traditional-use statements recorded.</p>}</div></ReviewContentBlock>
    <ReviewContentBlock title="Preparation traditions"><p>{plant.preparation || "No preparation information recorded."}</p></ReviewContentBlock>
    <RichReviewDetails plant={plant} sources={sources} mode="preparation" />
    <p className="border border-gold/40 bg-gold/10 p-4 font-sans text-xs leading-relaxed text-deep">Traditional use does not establish clinical effectiveness and does not replace professional medical advice.</p>
  </div>

  if (section === "safety") return <div className="grid gap-4">
    <ReviewContentBlock title="Safety, contraindications, and cautions"><ul className="grid gap-3">{plant.safety_notes.length ? plant.safety_notes.map((note) => <li key={note.category + note.statement} className="border-l-2 border-rust pl-3"><strong className="text-deep">{note.category}:</strong> {note.statement}</li>) : <li>No safety evidence recorded.</li>}</ul></ReviewContentBlock>
    <ReviewContentBlock title="Evidence strength and limitations"><p>{plant.evidence_notes || "No evidence limitations recorded."}</p></ReviewContentBlock>
    <RichReviewDetails plant={plant} sources={sources} mode="evidence" />
  </div>

  return <div className="grid gap-4">
    <div className="flex flex-wrap gap-2">{checks.map(([label, ready]) => <span key={label} className={"px-2.5 py-1 font-sans text-[10px] font-bold uppercase tracking-[.08em] " + (ready ? "bg-sage/30 text-forest" : "bg-rust/15 text-rust")}>{label}: {ready ? "ready" : "missing"}</span>)}</div>
    <ReviewContentBlock title="Distribution readiness"><p>{plant.distribution_summary || "No distribution summary recorded."}</p><ul aria-label="Distribution regions" className="mt-3 grid gap-1 text-xs">{plant.distribution.map((region) => <li key={region.status + region.code}><strong className="capitalize text-deep">{region.status}:</strong> {region.name}</li>)}</ul><PlantDistributionMap plant={distributionPlant} /></ReviewContentBlock>
    <ReviewContentBlock title="Information sources"><ol className="grid gap-3">{informationSources.length ? informationSources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noreferrer" className="font-bold text-deep hover:text-leaf">{source.title}</a><span className="block text-xs">{source.publisher} / {source.source_type} / {source.license_status}</span></li>) : <li>No information sources linked.</li>}</ol></ReviewContentBlock>
    <p className="font-sans text-xs leading-relaxed text-muted">Image rights and attribution are reviewed separately in the Overview section.</p>
  </div>
}


function RichReviewDetails({ plant, sources, mode }: { plant: ReviewablePlant; sources: ApiPlantDetail["sources"]; mode: "preparation" | "evidence" }) {
  const details = plant.article_details
  const preparationForms = details?.preparation_forms ?? []
  const evidenceFindings = details?.evidence_findings ?? []
  const mechanisms = details?.mechanisms ?? []
  const specialPopulations = details?.special_populations ?? []
  const interactions = details?.interactions ?? []
  const links = (ids: string[]) => <div className="mt-2 flex flex-wrap gap-2">{ids.map((id) => { const source = sources.find((item) => item.external_identifier === id); return source ? <a key={id} href={source.url} target="_blank" rel="noreferrer" className="font-sans text-[10px] font-bold uppercase text-leaf">{source.publisher}: {source.title}</a> : null })}</div>
  if (mode === "preparation") return preparationForms.length ? <ReviewContentBlock title="Preparation-specific forms"><div className="grid gap-4">{preparationForms.map((form) => <article key={form.label}><p className="font-bold text-deep">{form.label} <span className="font-normal text-muted">/ {form.route} / {form.plant_part}</span></p><p className="mt-1">{form.description}</p><p className="mt-2 border-l-2 border-gold pl-3 text-xs">{form.equivalence_warning}</p>{links(form.source_ids)}</article>)}</div></ReviewContentBlock> : null
  return <div className="grid gap-4">
    {evidenceFindings.length ? <ReviewContentBlock title="Evidence findings">{evidenceFindings.map((item) => <article key={item.heading} className="mb-4 last:mb-0"><p className="font-bold text-deep">{item.heading} <span className="font-normal text-muted">/ {item.evidence_level.replace("_", " ")} / {item.preparation}</span></p><p className="mt-1">{item.summary}</p><p className="mt-2 text-xs"><strong>Limitations:</strong> {item.limitations}</p>{links(item.source_ids)}</article>)}</ReviewContentBlock> : null}
    {mechanisms.length ? <ReviewContentBlock title="How it may work">{mechanisms.map((item) => <article key={item.preparation} className="mb-3 last:mb-0"><strong className="text-deep">{item.preparation}:</strong> {item.summary}<p className="mt-1 text-xs">{item.qualification}</p>{links(item.source_ids)}</article>)}</ReviewContentBlock> : null}
    {specialPopulations.length ? <ReviewContentBlock title="Special populations">{specialPopulations.map((item) => <article key={item.population} className="mb-3 last:mb-0"><strong className="text-deep">{item.population}:</strong> {item.guidance}{links(item.source_ids)}</article>)}</ReviewContentBlock> : null}
    {interactions.length ? <ReviewContentBlock title="Interactions">{interactions.map((item) => <article key={item.interaction}><strong className="text-deep">{item.interaction}:</strong> {item.statement}<p className="mt-1 text-xs">Evidence: {item.evidence_level}</p>{links(item.source_ids)}</article>)}</ReviewContentBlock> : null}
  </div>
}

function ReviewContentBlock({ title, children, className = "" }: { title: string; children: ReactNode; className?: string }) {
  return <section className={`border border-line bg-sage/15 p-4 font-sans text-sm leading-relaxed text-muted ${className}`}><h4 className="font-serif text-xl font-semibold text-deep">{title}</h4><div className="mt-2">{children}</div></section>
}

function ProfileRevisions() {
  const pageSize = 6
  const revisions = useAsyncResource<ApiPlantRevision[]>(useCallback((signal: AbortSignal) => fetchPlantRevisions(signal), []))
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [reason, setReason] = useState("Needs additional editorial review.")
  const [message, setMessage] = useState("")
  const [busy, setBusy] = useState(false)
  const items = useMemo(() => revisions.data ?? [], [revisions.data])
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize))
  const safePage = Math.min(page, pageCount)
  const pageItems = useMemo(() => items.slice((safePage - 1) * pageSize, safePage * pageSize), [items, safePage])
  const selected = useMemo(() => pageItems.find((revision) => revision.id === selectedId) ?? pageItems[0] ?? null, [pageItems, selectedId])

  async function act(action: () => Promise<ApiPlantRevision>, success: string) {
    setBusy(true)
    setMessage("")
    try {
      await action()
      setMessage(success)
      revisions.reload()
    } catch (error) {
      setMessage(error instanceof ApiRequestError
        ? error.message
        : "Promotion could not be completed. No article changes were saved.")
    } finally {
      setBusy(false)
    }
  }

  return <><PageHeader eyebrow="Editorial / revisions" title="Profile Revisions" description="Compare improved corpus content with the current canonical article. Published content remains public until an approved revision is explicitly promoted." action={<button type="button" onClick={revisions.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream hover:bg-leaf">Refresh</button>} />
    {revisions.isLoading ? <AdminStateCard title="Loading profile revisions" description="Retrieving current and proposed article versions." /> : null}
    {revisions.error ? <AdminStateCard title="Profile revisions unavailable" description="The revision queue could not be loaded." action={<button type="button" onClick={revisions.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Try again</button>} /> : null}
    {revisions.data && !items.length ? <AdminStateCard title="No profile revisions" description="Newer manifest content will appear here without replacing canonical articles." /> : null}
    {items.length ? <section aria-label="Profile revision workspace" className="grid items-stretch gap-5 xl:grid-cols-[.48fr_1.52fr]">
      <Panel eyebrow="Pending content" title="Revision queue" className="h-full"><div className="grid gap-3">{pageItems.map((revision) => {
        const isSelected = selected?.id === revision.id
        return <button key={revision.id} type="button" aria-pressed={isSelected} onClick={() => setSelectedId(revision.id)} className={"border p-4 text-left " + (isSelected ? "border-leaf bg-sage/25" : "border-line bg-paper hover:border-leaf")}><div className="flex items-center justify-between gap-3"><AdminStatusPill>{revision.status}</AdminStatusPill><span className="font-sans text-xs text-muted">v{revision.current_version} to v{revision.proposed_version}</span></div><h2 className="mt-3 font-serif text-xl font-semibold text-deep">{revision.display_common_name}</h2></button>
      })}</div><QueuePagination page={safePage} pageCount={pageCount} onPrevious={() => setPage((current) => Math.max(1, current - 1))} onNext={() => setPage((current) => Math.min(pageCount, current + 1))} /></Panel>
      <Panel eyebrow="Current / proposed" title={selected?.display_common_name ?? "Select a revision"} className="flex h-full min-w-0 flex-col">{selected ? <RevisionComparison revision={selected} /> : null}
        {message ? <p role="alert" className="mt-4 border border-gold/40 bg-gold/10 p-3 font-sans text-sm text-deep">{message}</p> : null}
        {selected?.promotion_error_message && !selected.promotion_eligible ? <p className="mt-4 border border-line bg-sage/15 p-3 font-sans text-sm text-muted"><strong className="text-deep">Promotion status:</strong> {selected.promotion_error_message}</p> : null}
        {selected ? <div className="mt-auto flex flex-wrap items-end gap-3 border-t border-line pt-4"><button type="button" disabled={busy || !["needs_review", "held"].includes(selected.status)} onClick={() => act(() => approvePlantRevision(selected.id), "Revision approved. It remains private until promotion.")} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">{busy ? "Working..." : "Approve revision"}</button><button type="button" disabled={busy || !selected.promotion_eligible} onClick={() => act(() => promotePlantRevision(selected.id), "Approved revision promoted atomically.")} className="bg-leaf px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">{busy ? "Working..." : "Promote revision"}</button><label className="grid gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">Hold reason<input value={reason} onChange={(event) => setReason(event.target.value)} className="min-h-11 w-[min(25rem,70vw)] border border-line bg-paper px-3 font-sans text-sm font-normal normal-case tracking-normal text-deep" /></label><button type="button" disabled={busy || !reason.trim() || selected.status === "promoted" || selected.status === "superseded"} onClick={() => act(() => holdPlantRevision(selected.id, reason), "Revision held. Canonical public content is unchanged.")} className="border border-rust px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-rust disabled:opacity-40">{busy ? "Working..." : "Hold / reject"}</button></div> : null}
      </Panel>
    </section> : null}
  </>
}

function RevisionComparison({ revision }: { revision: ApiPlantRevision }) {
  return <div className="flex min-h-0 flex-1 flex-col">
    <div className="mb-4 flex flex-wrap items-center gap-3"><AdminStatusPill>{revision.status}</AdminStatusPill><span className="font-sans text-xs text-muted">Current v{revision.current_version}</span><GitCompareArrows size={15} className="text-leaf" /><span className="font-sans text-xs font-semibold text-forest">Proposed v{revision.proposed_version}</span></div>
    <ReviewSectionPager key={revision.id} selectionKey={revision.id} renderSection={(section) => <div className="grid gap-5 lg:grid-cols-2"><RevisionColumn label={`Current version ${revision.current_version}`} plant={revision.current_content} sources={revision.current_content.sources} section={section} status={revision.current_content.status} version={revision.current_version} /><RevisionColumn label={`Proposed version ${revision.proposed_version}`} plant={revision.proposed_content} sources={revision.proposed_sources} section={section} status={revision.status} version={revision.proposed_version} /></div>} />
    {revision.decision_reason ? <p className="mt-4 border border-rust/30 bg-rust/10 p-3 font-sans text-sm text-deep"><strong>Editorial reason:</strong> {revision.decision_reason}</p> : null}
  </div>
}

function RevisionColumn({ label, plant, sources, section, status, version }: { label: string; plant: ReviewablePlant; sources: ApiPlantDetail["sources"]; section: ReviewSectionId; status: string; version: number }) {
  return <article className="min-w-0 border border-line bg-paper p-4"><p className="hw-eyebrow mb-3">{label}</p><PlantReviewSection plant={plant} sources={sources} section={section} status={status} version={version} /></article>
}
function PipelineRuns() { const runs = useAsyncResource(useCallback((signal: AbortSignal) => fetchPipelineRuns(signal), [])); return <><PageHeader eyebrow="Operations / monitoring" title="Pipeline Runs" description="A clear record of every persisted HerbWire pipeline run and stage result." />{runs.isLoading ? <AdminStateCard title="Loading pipeline dashboard" description="Gathering run activity and stage history." /> : null}{runs.error ? <AdminStateCard title="Pipeline runs unavailable" description="The pipeline monitoring view could not be loaded." action={<button type="button" onClick={runs.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Try again</button>} /> : null}{runs.data ? <PipelinePanel runs={runs.data} /> : null}</> }

function PipelinePanel({ runs }: { runs: ApiPipelineRun[] }) { return <Panel eyebrow="Recent activity" title="Pipeline runs"><div className="grid gap-4">{runs.length ? runs.map((run) => <article key={run.id} className="border-t border-line pt-4 first:border-t-0 first:pt-0"><div className="flex flex-wrap items-center justify-between gap-3"><div><AdminStatusPill>{run.status}</AdminStatusPill><h3 className="mt-3 font-serif text-xl font-semibold text-deep">{run.pipeline_type}</h3><p className="mt-1 font-sans text-xs text-muted">{run.trigger} / {run.current_stage} / {new Date(run.started_at).toLocaleString()}</p></div></div><ol className="mt-3 list-decimal pl-5 font-sans text-xs leading-relaxed text-muted">{run.stages.map((stage) => <li key={`${run.id}-${stage.name}`}>{stage.name}: {stage.status} / {stage.duration_ms}ms</li>)}</ol></article>) : <p className="font-sans text-sm text-muted">No pipeline runs recorded.</p>}</div></Panel> }

function Flashes() { const [query, setQuery] = useState(""); const plants = useAsyncResource<ApiPlantListItem[]>(useCallback((signal: AbortSignal) => fetchPlants(undefined, signal), [])); const filtered = useMemo(() => (plants.data ?? []).filter((plant) => `${plant.display_common_name} ${plant.accepted_scientific_name}`.toLowerCase().includes(query.toLowerCase())), [plants.data, query]); return <><PageHeader eyebrow="Operations / live feed" title="Flashes" description="Published plant articles currently available through the live FastAPI and PostgreSQL-backed public archive." action={<span className="inline-flex items-center gap-2 border border-line px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-muted">Published profiles only</span>} />{plants.isLoading ? <AdminStateCard title="Loading flashes" description="Refreshing the live published plant feed for the desk." /> : null}{plants.error ? <AdminStateCard title="Flashes are unavailable" description="The published profile feed could not be loaded right now." action={<button type="button" onClick={plants.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Try again</button>} /> : null}{plants.data ? <><div className="mb-7 flex flex-col gap-3 border-b border-line pb-5 lg:flex-row lg:items-center"><div className="flex flex-1 items-center gap-2 border border-line bg-paper px-3 py-2"><Search size={15} className="text-muted" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search flashes" className="w-full bg-transparent font-sans text-sm text-deep outline-none placeholder:text-muted" /></div><span className="inline-flex items-center gap-2 font-sans text-xs text-muted"><Filter size={14} /> {filtered.length} flashes</span></div><div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{filtered.length ? filtered.map((plant) => <article key={plant.id} className="overflow-hidden border border-line bg-paper transition hover:-translate-y-0.5 hover:border-leaf"><div className="relative aspect-[1.7] overflow-hidden bg-sage/20"><BotanicalImage label={plant.display_common_name} image={plant.hero_image} /><span className="absolute left-3 top-3 inline-flex items-center gap-1.5 bg-cream/90 px-2.5 py-1 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest"><Zap size={12} /> Flash</span></div><div className="p-5"><div className="flex items-center justify-between gap-3"><span className="hw-eyebrow">Plant article</span><AdminStatusPill>{plant.status}</AdminStatusPill></div><h2 className="mt-3 font-serif text-2xl font-semibold leading-tight text-deep">{plant.display_common_name}</h2><p className="mt-2 font-sans text-xs italic text-muted">{plant.accepted_scientific_name}</p><p className="mt-4 font-sans text-xs leading-relaxed text-muted">{plant.summary}</p><div className="mt-5 flex items-center justify-between border-t border-line pt-3 font-sans text-[10px] uppercase tracking-[.1em] text-muted"><span>{plant.source_count} sources</span><Link to={`/plants/${plant.slug}`} className="font-bold text-leaf hover:text-forest">View public article</Link></div></div></article>) : <AdminStateCard title="No flashes match those filters" description="Try widening the search to see published plant articles." />}</div></> : null}</> }

function AgentPerformance() { const performance = useAsyncResource<ApiAgentPerformance>(useCallback((signal: AbortSignal) => fetchAgentPerformance(signal), [])); return <><PageHeader eyebrow="Operations / observability" title="Agent Performance" description="Truthful metrics from persisted HerbWire pipeline runs and stage results. No unimplemented agents or fabricated percentages are shown." />{performance.isLoading ? <AdminStateCard title="Loading performance data" description="Gathering throughput and reliability metrics from pipeline stage records." /> : null}{performance.error ? <AdminStateCard title="Performance data is unavailable" description="The observability view could not be loaded right now." action={<button type="button" onClick={performance.reload} className="bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream">Try again</button>} /> : null}{performance.data ? <PerformancePanel data={performance.data} /> : null}</> }

function PerformancePanel({ data }: { data: ApiAgentPerformance }) { const maxDuration = Math.max(...data.stages.map((stage) => stage.average_duration_ms), 0); return <><div className="mb-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Pipeline runs" value={String(data.total_runs)} detail="Persisted runs" /><Metric label="Succeeded" value={String(data.succeeded_runs)} detail="Runs marked succeeded" /><Metric label="Held" value={String(data.held_runs)} detail="Runs waiting on review" /><Metric label="Auto-published" value={String(data.auto_published)} detail="Must remain zero" /></div>{data.stages.length ? <><Panel eyebrow="Throughput" title="Average duration per implemented stage"><div className="space-y-4 pt-3">{data.stages.map((metric) => <div key={metric.name} className="grid grid-cols-[140px_1fr_70px] items-center gap-3"><span className="font-sans text-xs text-muted">{metric.name}</span><div className="h-3 bg-sage/25"><div className="h-full bg-leaf" style={{ width: maxDuration > 0 ? `${(metric.average_duration_ms / maxDuration) * 100}%` : "0%" }} /></div><span className="font-sans text-xs font-semibold text-forest">{metric.average_duration_ms}ms</span></div>)}</div></Panel><div className="mt-5 overflow-x-auto border border-line"><table className="w-full min-w-[760px] text-left"><thead className="bg-sage/15 font-sans text-[10px] font-bold uppercase tracking-[.12em] text-muted"><tr><th className="px-5 py-4">Stage</th><th>Total</th><th>Succeeded</th><th>Held</th><th>Failed</th><th>Skipped</th><th>Last status</th></tr></thead><tbody>{data.stages.map((metric) => <tr key={metric.name} className="border-t border-line font-sans text-sm"><td className="px-5 py-4 font-semibold text-deep">{metric.name}</td><td className="text-muted">{metric.total_runs}</td><td className="font-semibold text-leaf">{metric.succeeded}</td><td className="text-muted">{metric.held}</td><td className="text-muted">{metric.failed}</td><td className="text-muted">{metric.skipped}</td><td className="text-muted">{metric.last_status ?? "Not yet"}</td></tr>)}</tbody></table></div></> : <AdminStateCard title="No runs yet" description="Agent performance will appear after persisted pipeline stage records exist." />}</> }

function Sources() { return <><PageHeader eyebrow="Operations / sources" title="Sources" description="Source provenance is visible in each profile preview and public article. A dedicated source-health API is not implemented yet." /><AdminStateCard title="Source view pending" description="Use Review Queue to inspect source records attached to each database-backed plant profile." /></> }
