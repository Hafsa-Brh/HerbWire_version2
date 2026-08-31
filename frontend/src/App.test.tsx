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
  accepted_scientific_name: "Mentha x piperita L.",
  display_common_name: "Peppermint",
  family_name: "Lamiaceae",
  summary: "A reviewed peppermint summary from the API.",
  status: "published",
  hero_image: {
    label: "Botanical placeholder for peppermint",
    license_status: "No external image used.",
    attribution: "HerbWire local placeholder",
    alt_text: "Botanical placeholder for peppermint",
  },
  published_at: "2026-08-30T12:00:00Z",
  source_count: 3,
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

const plantDetail = {
  ...publishedPlant,
  introduction: "Reviewed introduction from the database.",
  botanical_description: "Kew-supported botanical description.",
  traditional_uses: [{ tradition: "European herbal medicine / EMA HMPC", statement: "Traditionally used language with attribution.", limitation: "Not a cure claim." }],
  parts_used: ["leaf", "essential oil"],
  distribution: ["Europe", "Central Asia"],
  preparation: "Documented infusion tradition without dosage.",
  safety_notes: ["Allergy caution."],
  evidence_notes: "Traditional use is not clinical proof.",
  last_reviewed_at: "2026-08-30T12:00:00Z",
  sources: [{ id: "source-record-1", url: "https://example.org/source", canonical_url: "https://example.org/source", title: "Source title", publisher: "Source publisher", source_type: "taxonomy", original_language: "en", license_status: "Citation and paraphrase only.", supports: { taxonomy: true, traditional_use: true }, accessed_at: "2026-08-30T12:00:00Z" }],
}

const draftReview = { id: "review-1", content_type: "plant_profile", status: "needs_review", reviewer_name: null, decision_reason: null, review_payload: { seed_slug: "german-chamomile" }, created_at: "2026-08-30T12:00:00Z", decided_at: null, plant_profile: { ...plantDetail, ...draftPlant } }
const publishedReview = { id: "review-2", content_type: "plant_profile", status: "approved", reviewer_name: "Local editor", decision_reason: null, review_payload: { seed_slug: "peppermint" }, created_at: "2026-08-30T12:00:00Z", decided_at: "2026-08-30T12:30:00Z", plant_profile: plantDetail }
const pipelineRun = { id: "run-1", pipeline_type: "curated_seed", trigger: "manual", provider: "local", idempotency_key: "seed-1", status: "succeeded", current_stage: "publisher", summary: {}, started_at: "2026-08-30T12:00:00Z", finished_at: "2026-08-30T12:01:00Z", stages: [{ name: "editorial_qa", status: "succeeded", attempt: 1, duration_ms: 10, input_refs: [], output_refs: [], error_code: null, error_message: null }] }
const performance = { total_runs: 1, succeeded_runs: 1, failed_runs: 0, held_runs: 0, auto_published: 0, last_execution: "2026-08-30T12:00:00Z", stages: [{ name: "editorial_qa", total_runs: 1, succeeded: 1, failed: 0, held: 0, skipped: 0, average_duration_ms: 10, last_status: "succeeded", last_completed_at: "2026-08-30T12:00:00Z" }] }

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }))
}

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

function installMockApi({ authenticated = true, plants = [publishedPlant], reviews = [draftReview, publishedReview] } = {}) {
  let authed = authenticated
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
    if (url.includes("/api/v1/plants")) return jsonResponse(plants)
    if (!authed && url.includes("/api/v1/admin/")) return jsonResponse({ detail: "Authentication required." }, 401)
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
    await screen.findByRole("heading", { name: "Editorial desk" })
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

    await screen.findByRole("heading", { name: "Editorial desk" })
    const reviewWorkspace = await screen.findByRole("region", { name: "Review workspace" })
    expect(reviewWorkspace).toHaveClass("lg:grid-cols-[.75fr_1.25fr]")
    expect(within(reviewWorkspace).getByText("Article review")).toBeInTheDocument()
    const nav = screen.getByRole("navigation", { name: "Editorial navigation" })
    expect(within(nav).getByRole("link", { name: /Flashes/i })).toHaveAttribute("href", "/admin/flashes")
    expect(within(nav).getByRole("link", { name: /Agent Performance/i })).toHaveAttribute("href", "/admin/agents")
    expect(screen.getByText("HB")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Logout" }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/auth/logout"), expect.objectContaining({ method: "POST" })))
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
    expect(screen.getByRole("heading", { name: "Qualified traditional uses" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Safety and contraindications" })).toBeInTheDocument()
    expect(screen.getByText("Source title")).toBeInTheDocument()
    expect(screen.queryByText("German chamomile")).not.toBeInTheDocument()
    const adminHeader = vi.mocked(fetch).mock.calls.find(([input]) => String(input).includes("/api/v1/admin/reviews"))?.[1]?.headers
    if (adminHeader) expect(adminHeader).not.toHaveProperty("X-HerbWire-Local-Editor")
  })

  it("supports review approve, hold, and publication gating through backend calls", async () => {
    installMockApi({ authenticated: true, reviews: [draftReview] })
    renderAt("/admin/review")

    await screen.findByRole("heading", { name: "Review Queue" })
    await screen.findByRole("button", { name: "Publish" })
    expect(screen.getByRole("button", { name: "Publish" })).toBeDisabled()
    fireEvent.click(screen.getByRole("button", { name: "Approve" }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/admin/reviews/review-1/approve"), expect.objectContaining({ method: "POST" })))
    fireEvent.change(screen.getByLabelText("Hold reason"), { target: { value: "Needs source check." } })
    fireEvent.click(screen.getByRole("button", { name: "Hold / reject" }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/admin/reviews/review-1/reject"), expect.objectContaining({ body: JSON.stringify({ reviewer_name: "Local editor", reason: "Needs source check." }) })))
  })
})
