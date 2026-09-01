import "@testing-library/jest-dom/vitest"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import App from "./App"

const TEST_EMAIL = "test-admin@example.invalid"
const TEST_PASSWORD = "test-password"

const publishedPlant = {
  id: "plant-1",
  slug: "peppermint",
  accepted_scientific_name: "Mentha × piperita L.",
  botanical_author: "L.",
  taxon_identifier: "urn:lsid:ipni.org:names:450969-1",
  known_synonyms: [],
  display_common_name: "Peppermint",
  family_name: "Lamiaceae",
  diversity_tags: ["Europe", "West Asia"],
  summary: "A reviewed peppermint summary from the API.",
  status: "published",
  hero_image: {
    kind: "licensed_photograph",
    local_path: "/media/plants/peppermint.jpg",
    source_page: "https://commons.wikimedia.org/wiki/File:Peppermint.jpg",
    attribution: "Test photographer, CC BY-SA 4.0, via Wikimedia Commons",
    license: "CC BY-SA 4.0",
    license_url: "https://creativecommons.org/licenses/by-sa/4.0",
    alt_text: "Botanical image of peppermint.",
    caption: "Peppermint",
  },
  published_at: "2026-08-30T12:00:00Z",
  source_count: 3,
  growth_form: "perennial herb",
  biome: "temperate",
  distribution_summary: "Europe to Central Asia",
  readiness_status: "ready_for_review",
  version: 1,
}

const draftPlant = {
  ...publishedPlant,
  id: "plant-2",
  slug: "german-chamomile",
  accepted_scientific_name: "Matricaria chamomilla L.",
  display_common_name: "German chamomile",
  family_name: "Asteraceae",
  summary: "Reviewed chamomile draft summary.",
  status: "needs_review",
  published_at: null,
}

const corpusPlants = Array.from({ length: 30 }, (_, index) => ({
  ...publishedPlant,
  id: "plant-" + (index + 1),
  slug: "plant-" + (index + 1),
  display_common_name: index === 18 ? "Asian ginseng" : "Plant " + String(index + 1).padStart(2, "0"),
  accepted_scientific_name: index === 18 ? "Panax ginseng C.A.Mey." : "Testus plantus " + (index + 1),
  family_name: index % 2 === 0 ? "Asteraceae" : "Lamiaceae",
  diversity_tags: index % 3 === 0 ? ["India"] : ["Europe"],
}))
const plantDetail = {
  ...publishedPlant,
  introduction: "Reviewed introduction from the database.",
  botanical_description: "Kew-supported botanical description.",
  traditional_uses: [{ tradition: "European herbal medicine / EMA HMPC", statement: "Traditionally used language with attribution.", limitation: "Not a cure claim." }],
  parts_used: ["leaf", "essential oil"],
  distribution: [{ code: "POWO-NATIVE-SUMMARY", name: "Europe to Central Asia", status: "native", level: 0, map_countries: ["FR", "DE", "IT"] }, { code: "POWO-INTRODUCED-LIST", name: "Introduced elsewhere", status: "introduced", level: 0, map_countries: ["US", "CA"] }],
  preparation: "Documented infusion tradition without dosage.",
  safety_notes: [{ category: "Safety", statement: "Allergy caution.", source: "test-source" }],
  evidence_notes: "Traditional use is not clinical proof.",
  article_details: { preparation_forms: [{ label: "Enteric-coated peppermint oil", plant_part: "essential oil", route: "oral", description: "Studied oral oil product.", equivalence_warning: "Not equivalent to peppermint leaf tea.", source_ids: ["test-info"] }], evidence_findings: [{ heading: "Adult irritable bowel syndrome", preparation: "enteric-coated oral oil", evidence_level: "limited", summary: "A source-led evidence summary.", limitations: "Preparation-specific evidence remains limited.", source_ids: ["test-info"] }], mechanisms: [{ preparation: "peppermint oil", summary: "A proposed smooth-muscle action.", qualification: "A proposed mechanism does not prove benefit.", source_ids: ["test-info"] }], special_populations: [{ population: "Infants and young children", guidance: "Preparation-specific caution.", source_ids: ["test-info"] }], interactions: [{ interaction: "Other medicines", evidence_level: "uncertain", statement: "Seek professional advice.", source_ids: ["test-info"] }], section_sources: { evidence: ["test-info"], safety: ["test-info"] } },
  last_reviewed_at: "2026-08-30T12:00:00Z",
  sources: [{ id: "source-record-1", external_identifier: "test-info", url: "https://example.org/source", canonical_url: "https://example.org/source", title: "Source title", publisher: "Source publisher", source_type: "taxonomy", original_language: "en", license_status: "Citation and paraphrase only.", supports: { taxonomy: true, distribution: true, traditional_use: true }, accessed_at: "2026-08-30T12:00:00Z" }, { id: "source-record-2", external_identifier: "test-media", url: "https://commons.wikimedia.org/wiki/File:Peppermint.jpg", canonical_url: "https://commons.wikimedia.org/wiki/File:Peppermint.jpg", title: "Peppermint image source", publisher: "Wikimedia Commons", source_type: "licensed_media", original_language: "en", license_status: "CC BY-SA 4.0", supports: { media: true }, accessed_at: "2026-08-30T12:00:00Z" }],
}

const draftReview = { id: "review-1", content_type: "plant_profile", status: "needs_review", reviewer_name: null, decision_reason: null, review_payload: { seed_slug: "german-chamomile" }, created_at: "2026-08-30T12:00:00Z", decided_at: null, plant_profile: { ...plantDetail, ...draftPlant } }
const publishedReview = { id: "review-2", content_type: "plant_profile", status: "approved", reviewer_name: "Local editor", decision_reason: null, review_payload: { seed_slug: "peppermint" }, created_at: "2026-08-30T12:00:00Z", decided_at: "2026-08-30T12:30:00Z", plant_profile: plantDetail }
const pipelineRun = { id: "run-1", pipeline_type: "curated_seed", trigger: "manual", provider: "local", idempotency_key: "seed-1", status: "succeeded", current_stage: "publisher", summary: {}, started_at: "2026-08-30T12:00:00Z", finished_at: "2026-08-30T12:01:00Z", stages: [{ name: "editorial_qa", status: "succeeded", attempt: 1, duration_ms: 10, input_refs: [], output_refs: [], error_code: null, error_message: null }] }
const performance = { total_runs: 1, succeeded_runs: 1, failed_runs: 0, held_runs: 0, auto_published: 0, last_execution: "2026-08-30T12:00:00Z", stages: [{ name: "editorial_qa", total_runs: 1, succeeded: 1, failed: 0, held: 0, skipped: 0, average_duration_ms: 10, last_status: "succeeded", last_completed_at: "2026-08-30T12:00:00Z" }] }
const plantRevision = {
  id: "revision-1",
  plant_profile_id: publishedPlant.id,
  slug: publishedPlant.slug,
  display_common_name: publishedPlant.display_common_name,
  current_version: 1,
  proposed_version: 3,
  status: "needs_review",
  content_checksum: "a".repeat(64),
  current_content: plantDetail,
  proposed_content: { ...plantDetail, version: undefined, sources: undefined, source_count: undefined, published_at: undefined, last_reviewed_at: undefined, status: undefined, id: undefined, slug: undefined, introduction: "Expanded version-three overview from the corpus manifest.", evidence_notes: "Version-three evidence limitations remain explicit." },
  proposed_sources: plantDetail.sources.filter((source) => source.source_type !== "licensed_media"),
  reviewer_name: null,
  decision_reason: null,
  created_at: "2026-09-01T12:00:00Z",
  reviewed_at: null,
  promoted_at: null,
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }))
}

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

function installMockApi({ authenticated = true, plants = [publishedPlant], reviews = [draftReview, publishedReview], revisions = [plantRevision], revisionFailure = false } = {}) {
  let authed = authenticated
  let revisionStatus = revisions[0]?.status ?? "needs_review"
  let revisionFailures = revisionFailure ? 1 : 0
  vi.mocked(fetch).mockImplementation((input, init) => {
    const url = String(input)
    if (url.endsWith("/api/v1/auth/session")) return jsonResponse({ authenticated: authed, user: authed ? { initials: "HB", label: "Local admin", role: "Milestone 2 editor" } : null })
    if (url.endsWith("/api/v1/auth/login")) {
      const body = JSON.parse(String(init?.body ?? "{}"))
      authed = body.email === TEST_EMAIL && body.password === TEST_PASSWORD
      return jsonResponse({ authenticated: authed, user: authed ? { initials: "HB", label: "Local admin", role: "Milestone 2 editor" } : null }, authed ? 200 : 401)
    }
    if (url.endsWith("/api/v1/auth/logout")) { authed = false; return jsonResponse({ authenticated: false, user: null }) }
    if (url.endsWith("/api/v1/newsletter/subscriptions")) {
      const body = JSON.parse(String(init?.body ?? "{}"))
      if (!String(body.email).includes("@")) return jsonResponse({ detail: "Enter a valid email address." }, 422)
      return jsonResponse({ email: String(body.email).trim().toLowerCase(), status: String(body.email).includes("again") ? "already_subscribed" : "subscribed", created_at: "2026-08-31T12:00:00Z" })
    }
    if (url.includes("/api/v1/plants/peppermint")) return jsonResponse(plantDetail)
    if (url.includes("/api/v1/plants")) {
      const parsed = new URL(url)
      const query = (parsed.searchParams.get("query") ?? "").toLowerCase()
      const family = parsed.searchParams.get("family") ?? ""
      const tag = parsed.searchParams.get("tag") ?? ""
      const page = Number(parsed.searchParams.get("page") ?? "1")
      const pageSize = Number(parsed.searchParams.get("page_size") ?? "12")
      const filtered = plants.filter((plant) => {
        const names = (plant.display_common_name + " " + plant.accepted_scientific_name).toLowerCase()
        return (!query || names.includes(query)) && (!family || plant.family_name === family) && (!tag || plant.diversity_tags.includes(tag))
      })
      const items = filtered.slice((page - 1) * pageSize, page * pageSize)
      return jsonResponse({ items, total: filtered.length, page, page_size: pageSize, pages: Math.max(1, Math.ceil(filtered.length / pageSize)) })
    }
    if (!authed && url.includes("/api/v1/admin/")) return jsonResponse({ detail: "Authentication required." }, 401)
    if (url.endsWith("/api/v1/admin/revisions") && !init?.method) { if (revisionFailures > 0) { revisionFailures -= 1; return jsonResponse({ detail: "Unavailable" }, 503) }; return jsonResponse(revisions.map((revision) => ({ ...revision, status: revisionStatus }))) }
    if (url.includes("/api/v1/admin/revisions/") && url.endsWith("/approve") && init?.method === "POST") { revisionStatus = "approved"; return jsonResponse({ ...revisions[0], status: revisionStatus }) }
    if (url.includes("/api/v1/admin/revisions/") && url.endsWith("/reject") && init?.method === "POST") { revisionStatus = "held"; return jsonResponse({ ...revisions[0], status: revisionStatus }) }
    if (url.includes("/api/v1/admin/revisions/") && url.endsWith("/promote") && init?.method === "POST") { if (revisionStatus !== "approved") return jsonResponse({ detail: "Approval required." }, 409); revisionStatus = "promoted"; return jsonResponse({ ...revisions[0], status: revisionStatus }) }
    if (url.endsWith("/api/v1/admin/reviews") && !init?.method) return jsonResponse(reviews)
    if (url.endsWith("/api/v1/admin/pipeline/runs")) return jsonResponse([pipelineRun])
    if (url.endsWith("/api/v1/admin/agent-performance")) return jsonResponse(performance)
    if (url.includes("/approve") && init?.method === "POST") return jsonResponse({ ...draftReview, status: "approved" })
    if (url.includes("/reject") && init?.method === "POST") return jsonResponse({ ...draftReview, status: "held" })
    if (url.includes("/publish") && init?.method === "POST") return jsonResponse({ ...plantDetail, status: "published" })
    return jsonResponse({})
  })
}

describe("Milestone 2 final UI and functionality", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn()))
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

  it("keeps public navigation limited and restores the original subscription section", async () => {
    installMockApi()
    renderAt("/")

    const nav = screen.getByRole("navigation", { name: "Primary navigation" })
    expect(within(nav).getByRole("link", { name: "Plants" })).toHaveAttribute("href", "/plants")
    expect(within(nav).getByRole("link", { name: "New Discoveries" })).toHaveAttribute("href", "/discoveries")
    expect(within(nav).queryByText("Health")).not.toBeInTheDocument()
    expect(screen.getByLabelText("HerbWire home")).toHaveAttribute("href", "/")
    await screen.findByRole("heading", { name: "A little green in your inbox." })
    expect(screen.queryByRole("heading", { name: "A little humility in every profile." })).not.toBeInTheDocument()
  })

  it("subscribes, handles duplicate subscriptions, and validates invalid email", async () => {
    installMockApi()
    renderAt("/")
    const input = await screen.findByLabelText("Email address")
    fireEvent.change(input, { target: { value: "reader@example.com" } })
    fireEvent.click(screen.getByRole("button", { name: "Subscribe" }))
    await screen.findByText(/You are subscribed/i)
    fireEvent.change(input, { target: { value: "again@example.com" } })
    fireEvent.click(screen.getByRole("button", { name: "Subscribe" }))
    await screen.findByText(/already subscribed/i)
    fireEvent.change(input, { target: { value: "bad" } })
    fireEvent.click(screen.getByRole("button", { name: "Subscribe" }))
    await screen.findByText(/valid email/i)
  })

  it("removes the login image headline and keeps the required bottom text", () => {
    installMockApi({ authenticated: false })
    renderAt("/login")

    expect(screen.queryByText("A clearer way to tend the wire.")).not.toBeInTheDocument()
    expect(screen.getByText("Shape careful medicinal-plant profiles with provenance, safety checks, and human publication control.")).toBeInTheDocument()
  })

  it("rejects incorrect login and authenticates correct test credentials", async () => {
    installMockApi({ authenticated: false })
    renderAt("/login")

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: TEST_EMAIL } })
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } })
    fireEvent.click(screen.getByRole("button", { name: "Enter editorial desk" }))
    await screen.findByRole("alert")

    fireEvent.change(screen.getByLabelText("Password"), { target: { value: TEST_PASSWORD } })
    fireEvent.click(screen.getByRole("button", { name: "Enter editorial desk" }))
    await screen.findByRole("heading", { name: "Dashboard" })
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/auth/login",
      expect.objectContaining({ method: "POST", credentials: "include" }),
    )
  })

  it("redirects unauthenticated admin access to login", async () => {
    installMockApi({ authenticated: false })
    renderAt("/admin")

    await screen.findByRole("heading", { name: "Sign in to the desk" })
  })

  it("renders authenticated admin navigation, HB avatar, and logout", async () => {
    installMockApi({ authenticated: true })
    renderAt("/admin")

    await screen.findByRole("heading", { name: "Dashboard" })
    expect(screen.getByRole("heading", { name: "No operational dashboard yet" })).toBeInTheDocument()
    expect(screen.queryByRole("region", { name: "Review workspace" })).not.toBeInTheDocument()
    const nav = screen.getByRole("navigation", { name: "Editorial navigation" })
    expect(within(nav).getByRole("link", { name: /Review Queue/i })).toHaveAttribute("href", "/admin/reviews")
    expect(within(nav).getByRole("link", { name: /Flashes/i })).toHaveAttribute("href", "/admin/flashes")
    expect(within(nav).getByRole("link", { name: /Agent Performance/i })).toHaveAttribute("href", "/admin/agents")
    expect(screen.getByText("HB")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Logout" }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/auth/logout"), expect.objectContaining({ method: "POST" })))
  })

  it("paginates review sections, preserves all content, and resets on plant selection", async () => {
    const reviews = Array.from({ length: 7 }, (_, index) => ({
      ...draftReview,
      id: `review-${index + 1}`,
      plant_profile: { ...draftReview.plant_profile, id: `draft-${index + 1}`, display_common_name: `Review plant ${index + 1}` },
    }))
    installMockApi({ authenticated: true, reviews })
    renderAt("/admin/reviews")

    await screen.findByRole("heading", { name: "Review Queue" })
    const workspace = await screen.findByRole("region", { name: "Review workspace" })
    expect(workspace).toHaveClass("items-stretch", "lg:grid-cols-[.75fr_1.25fr]")
    expect(within(workspace).getByText("Article review")).toBeInTheDocument()
    expect(within(workspace).getByRole("heading", { name: "Overview" })).toBeInTheDocument()
    expect(within(workspace).getByText("Section 1 of 5")).toBeInTheDocument()
    const sectionNav = within(workspace).getByRole("navigation", { name: "Article review sections" })
    for (const section of ["Overview", "Botanical content", "Traditional use & preparation", "Safety & evidence", "Distribution & sources"]) {
      expect(within(sectionNav).getByRole("button", { name: `Open ${section} section` })).toBeInTheDocument()
    }
    const previousSection = within(workspace).getByRole("button", { name: "Previous review section" })
    const nextSection = within(workspace).getByRole("button", { name: "Next review section" })
    expect(previousSection).toBeDisabled()
    expect(within(workspace).getByText(/Media attribution:/i)).toBeInTheDocument()

    const mutationCallsBefore = vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method === "POST").length
    fireEvent.click(nextSection)
    const botanicalHeading = await within(workspace).findByRole("heading", { name: "Botanical content" })
    expect(botanicalHeading).toHaveFocus()
    expect(within(workspace).getByText("Kew-supported botanical description.")).toBeInTheDocument()
    fireEvent.click(previousSection)
    expect(await within(workspace).findByRole("heading", { name: "Overview" })).toHaveFocus()

    fireEvent.click(within(sectionNav).getByRole("button", { name: "Open Safety & evidence section" }))
    expect(await within(workspace).findByRole("heading", { name: "Safety & evidence" })).toHaveFocus()
    expect(within(workspace).getByText(/Allergy caution/i)).toBeInTheDocument()
    expect(within(workspace).getByText(/Traditional use is not clinical proof/i)).toBeInTheDocument()

    fireEvent.click(within(sectionNav).getByRole("button", { name: "Open Distribution & sources section" }))
    expect(await within(workspace).findByRole("heading", { name: "Distribution & sources" })).toHaveFocus()
    expect(nextSection).toBeDisabled()
    expect(await within(workspace).findByRole("img", { name: "Country-level distribution overview for Review plant 1" }, { timeout: 8000 })).toBeInTheDocument()
    expect(within(workspace).getByLabelText("Map legend")).toBeInTheDocument()
    expect(within(workspace).getByText("Source title")).toBeInTheDocument()
    expect(within(workspace).queryByText("Peppermint image source")).not.toBeInTheDocument()
    expect(within(workspace).getByText(/Image rights and attribution are reviewed separately/i)).toBeInTheDocument()
    const mutationCallsAfter = vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method === "POST").length
    expect(mutationCallsAfter).toBe(mutationCallsBefore)

    fireEvent.click(within(workspace).getByRole("button", { name: /Review plant 2/i }))
    expect(await within(workspace).findByRole("heading", { name: "Overview" })).toBeInTheDocument()
    expect(within(workspace).getAllByRole("heading", { name: "Review plant 2" }).length).toBeGreaterThanOrEqual(2)
    expect(within(workspace).getByRole("button", { name: /Review plant 2/i })).toHaveAttribute("aria-pressed", "true")

    expect(within(workspace).getByText("Page 1 of 2")).toBeInTheDocument()
    expect(within(workspace).queryByText("Review plant 7")).not.toBeInTheDocument()
    fireEvent.click(within(workspace).getByRole("button", { name: "Next queue page" }))
    expect(await within(workspace).findAllByText("Review plant 7")).not.toHaveLength(0)
    expect(within(workspace).getByText("Page 2 of 2")).toBeInTheDocument()
  }, 15000)
  it("paginates revision comparison sections and preserves workflow gating", async () => {
    installMockApi({ authenticated: true })
    renderAt("/admin/revisions")

    await screen.findByRole("heading", { name: "Profile Revisions" })
    const workspace = await screen.findByRole("region", { name: "Profile revision workspace" })
    expect(await within(workspace).findByText("Current version 1")).toBeInTheDocument()
    expect(within(workspace).getByText("Proposed version 3")).toBeInTheDocument()
    expect(within(workspace).getByText("Expanded version-three overview from the corpus manifest.")).toBeInTheDocument()
    const promote = within(workspace).getByRole("button", { name: "Promote revision" })
    expect(promote).toBeDisabled()
    expect(within(workspace).getByRole("button", { name: "Previous review section" })).toBeDisabled()

    const mutationCallsBefore = vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method === "POST").length
    fireEvent.click(within(workspace).getByRole("button", { name: "Open Traditional use & preparation section" }))
    expect(await within(workspace).findByRole("heading", { name: "Traditional use & preparation" })).toHaveFocus()
    expect(within(workspace).getAllByText(/Documented infusion tradition without dosage/i)).toHaveLength(2)
    fireEvent.click(within(workspace).getByRole("button", { name: "Open Safety & evidence section" }))
    expect(within(workspace).getAllByText(/Allergy caution/i)).toHaveLength(2)
    fireEvent.click(within(workspace).getByRole("button", { name: "Open Distribution & sources section" }))
    expect(await within(workspace).findAllByRole("img", { name: "Country-level distribution overview for Peppermint" }, { timeout: 8000 })).toHaveLength(2)
    expect(within(workspace).getAllByLabelText("Map legend")).toHaveLength(2)
    expect(within(workspace).getAllByText("Source title")).toHaveLength(2)
    expect(within(workspace).queryByText("Peppermint image source")).not.toBeInTheDocument()
    expect(within(workspace).getByRole("button", { name: "Next review section" })).toBeDisabled()
    const mutationCallsAfter = vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method === "POST").length
    expect(mutationCallsAfter).toBe(mutationCallsBefore)

    fireEvent.click(within(workspace).getByRole("button", { name: "Approve revision" }))
    await waitFor(() => expect(promote).toBeEnabled())
    fireEvent.click(promote)
    expect(await within(workspace).findByText("Approved revision promoted atomically.")).toBeInTheDocument()
  }, 15000)

  it("paginates the profile revision queue and resets comparison sections", async () => {
    const revisions = Array.from({ length: 7 }, (_, index) => ({
      ...plantRevision,
      id: `revision-${index + 1}`,
      display_common_name: `Revision plant ${index + 1}`,
      current_content: { ...plantDetail, display_common_name: `Revision plant ${index + 1}` },
      proposed_content: { ...plantRevision.proposed_content, display_common_name: `Revision plant ${index + 1}` },
    }))
    installMockApi({ authenticated: true, revisions })
    renderAt("/admin/revisions")

    const workspace = await screen.findByRole("region", { name: "Profile revision workspace" })
    fireEvent.click(within(workspace).getByRole("button", { name: "Open Safety & evidence section" }))
    expect(await within(workspace).findByRole("heading", { name: "Safety & evidence" })).toBeInTheDocument()
    expect(within(workspace).getByText("Page 1 of 2")).toBeInTheDocument()
    expect(within(workspace).queryByText("Revision plant 7")).not.toBeInTheDocument()
    fireEvent.click(within(workspace).getByRole("button", { name: "Next queue page" }))
    expect(await within(workspace).findAllByText("Revision plant 7")).not.toHaveLength(0)
    expect(within(workspace).getByRole("heading", { name: "Overview" })).toBeInTheDocument()
    expect(within(workspace).getByRole("button", { name: /Revision plant 7/i })).toHaveAttribute("aria-pressed", "true")
    expect(within(workspace).getByText("Page 2 of 2")).toBeInTheDocument()
  })
  it("holds a pending revision with an editorial reason", async () => {
    installMockApi({ authenticated: true })
    renderAt("/admin/revisions")

    await screen.findByRole("heading", { name: "Profile Revisions" })
    fireEvent.change(await screen.findByLabelText("Hold reason"), { target: { value: "Safety citation needs review." } })
    fireEvent.click(screen.getByRole("button", { name: "Hold / reject" }))
    expect(await screen.findByText("Revision held. Canonical public content is unchanged.")).toBeInTheDocument()
  })

  it("renders revision empty and retry states", async () => {
    installMockApi({ authenticated: true, revisions: [], revisionFailure: true })
    renderAt("/admin/revisions")

    expect(await screen.findByRole("heading", { name: "Profile revisions unavailable" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Try again" }))
    expect(await screen.findByRole("heading", { name: "No profile revisions" })).toBeInTheDocument()
  })
  it("renders Flashes from real response-shaped published plant data", async () => {
    installMockApi({ authenticated: true })
    renderAt("/admin/flashes")

    await screen.findByRole("heading", { name: "Flashes" })
    expect(await screen.findByRole("heading", { name: "Peppermint" })).toBeInTheDocument()
    expect(screen.getByText(/Published profiles only/i)).toBeInTheDocument()
  })

  it("renders Agent Performance from pipeline metrics", async () => {
    installMockApi({ authenticated: true })
    renderAt("/admin/agents")

    await screen.findByRole("heading", { name: "Agent Performance" })
    expect((await screen.findAllByText("editorial_qa")).length).toBeGreaterThan(0)
    expect(screen.getByText("Auto-published")).toBeInTheDocument()
    expect(screen.getAllByText("0").length).toBeGreaterThan(0)
  })

  it("keeps draft plants absent publicly and renders complete peppermint detail", async () => {
    installMockApi({ plants: [publishedPlant] })
    renderAt("/plants/peppermint")

    await screen.findByRole("heading", { name: "Peppermint" })
    const overview = screen.getByTestId("article-overview")
    expect(within(overview).getByText(/Reviewed introduction from the database/i)).toBeInTheDocument()
    expect(within(overview).getByRole("heading", { name: "How Much Do We Know?" })).toBeInTheDocument()
    expect(within(overview).getByText(/Traditional use is not clinical proof/i)).toBeInTheDocument()
    expect(within(overview).queryByText(/Kew-supported botanical description/i)).not.toBeInTheDocument()
    expect(within(overview).queryByText(/Documented infusion tradition/i)).not.toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Botanical identity" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Preparation traditions" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Preparation and product forms" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "What have we learned?" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "How it may work" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Who should avoid it or seek advice?" })).toBeInTheDocument()
    expect(screen.getByText("Not equivalent to peppermint leaf tea.")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Qualified traditional uses" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Safety and contraindications" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Geographical distribution" })).toBeInTheDocument()
    expect(screen.getByLabelText("Distribution legend")).toBeInTheDocument()
    expect(await screen.findByRole("img", { name: "Country-level distribution overview for Peppermint" }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByLabelText("Map legend")).toBeInTheDocument()
    expect(screen.getByText("Origin uncertain")).toBeInTheDocument()
    expect(screen.getAllByText(/CC BY-SA 4.0/i).length).toBeGreaterThan(0)
    expect(screen.getByText("Source title")).toBeInTheDocument()
    expect(screen.queryByText("Peppermint image source")).not.toBeInTheDocument()
    expect(screen.queryByText("German chamomile")).not.toBeInTheDocument()
    const adminHeader = vi.mocked(fetch).mock.calls.find(([input]) => String(input).includes("/api/v1/admin/reviews"))?.[1]?.headers
    if (adminHeader) expect(adminHeader).not.toHaveProperty("X-HerbWire-Local-Editor")
  })

  it("supports review approve, hold, and publication gating through backend calls", async () => {
    installMockApi({ authenticated: true, reviews: [draftReview] })
    renderAt("/admin/reviews")

    await screen.findByRole("heading", { name: "Review Queue" })
    await screen.findByRole("button", { name: "Publish" })
    expect(screen.getByRole("button", { name: "Publish" })).toBeDisabled()
    fireEvent.click(screen.getByRole("button", { name: "Approve" }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/admin/reviews/review-1/approve"), expect.objectContaining({ method: "POST" })))
    fireEvent.change(screen.getByLabelText("Hold reason"), { target: { value: "Needs source check." } })
    fireEvent.click(screen.getByRole("button", { name: "Hold / reject" }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/admin/reviews/review-1/reject"), expect.objectContaining({ body: JSON.stringify({ reviewer_name: "Local editor", reason: "Needs source check." }) })))
  })

  it("pages, searches, and filters a 30-profile response", async () => {
    installMockApi({ plants: corpusPlants })
    renderAt("/plants")

    await screen.findByRole("heading", { name: "Plant 01" })
    expect(screen.getByRole("heading", { name: "MEDICINAL PLANTS" })).toBeInTheDocument()
    expect(screen.queryByText("Plant encyclopedia")).not.toBeInTheDocument()
    expect(screen.queryByText("Medicinal plant profiles")).not.toBeInTheDocument()
    expect(screen.getByText("30 published")).toBeInTheDocument()
    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Next/i }))
    await screen.findByRole("heading", { name: "Plant 13" })

    fireEvent.change(screen.getByLabelText("Search plant profiles"), { target: { value: "Panax" } })
    fireEvent.change(screen.getByLabelText("Filter by family"), { target: { value: "Asteraceae" } })
    fireEvent.change(screen.getByLabelText("Filter by region or tradition"), { target: { value: "India" } })
    fireEvent.click(screen.getByRole("button", { name: "Search" }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("query=Panax"), expect.anything()))
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("family=Asteraceae"), expect.anything())
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("tag=India"), expect.anything())
  })

  it("shows the plant API error state and retries", async () => {
    let failed = false
    vi.mocked(fetch).mockImplementation((input) => {
      if (String(input).includes("/api/v1/plants")) {
        if (!failed) {
          failed = true
          return jsonResponse({ detail: "Unavailable" }, 503)
        }
        return jsonResponse({ items: [publishedPlant], total: 1, page: 1, page_size: 12, pages: 1 })
      }
      return jsonResponse({ authenticated: false, user: null })
    })
    renderAt("/plants")

    await screen.findByRole("heading", { name: "The encyclopedia API is unavailable." })
    fireEvent.click(screen.getByRole("button", { name: "Try again" }))
    await screen.findByRole("heading", { name: "Peppermint" })
  })})
