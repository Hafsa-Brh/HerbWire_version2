import "@testing-library/jest-dom/vitest"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import App from "./App"

const discovery = {
  id: "discovery-1",
  slug: "pubmed-39900001",
  status: "needs_review",
  headline: "Safety evidence concerning Zingiber officinale",
  standfirst: "A PubMed-indexed record entered human editorial review.",
  body_blocks: [{ heading: "What the source reports", text: "A bounded source report.", source_record_ids: ["source-1"] }],
  limitations: ["The full paper was not assessed."],
  safety_context: "This draft does not establish safety or efficacy.",
  cannot_conclude: ["No treatment recommendation can be made."],
  qa_payload: { passed: true, reason_codes: [], checklist: { source_linked: true } },
  version: 1,
  content_origin: "curated",
  article_type: "Randomized controlled trial",
  research_date: null,
  research_question: "What did the trial test?",
  research_context: "A structured research context.",
  study_design: "Randomized and controlled.",
  evidence_base: "Eighty participants.",
  intervention: "A defined botanical preparation.",
  comparator: "Placebo.",
  main_findings: ["A bounded finding."],
  evidence_strength: "limited",
  evidence_strength_rationale: "One small trial.",
  why_matters: "It supports further research.",
  practical_interpretation: "This is not treatment advice.",
  section_sources: {},
  hero_image: { local_path: "/media/plants/ginger.jpg", alt_text: "Ginger", caption: "Botanical reference image; not an image from the reported study.", attribution: "Licensed image", license: "CC BY-SA 4.0" },
  geography: [],
  linked_plants: [{ id: "plant-1", slug: "ginger", common_name: "Ginger", scientific_name: "Zingiber officinale Roscoe", distribution: [{ code: "native", name: "South and Southeast Asia", status: "native", level: 0, map_countries: ["IN", "CN"] }], distribution_summary: "A verified WCVP-backed botanical range.", distribution_sources: [{ id: "distribution-source", provider: "kew", support_role: "distribution", external_identifier: "powo:ginger", pmid: null, doi: null, canonical_url: "https://powo.science.kew.org/", title: "Plants of the World Online", authors: [], journal: null, publication_date: null }] }],
  botanical_identity: null,
  category: "research_discovery_safety",
  relevance_reasons: ["supported_scientific_plant_name"],
  detected_entities: [{ label: "Zingiber officinale", scientific_name: "Zingiber officinale", ambiguous: false }],
  evidence_package: {
    evidence_type: "clinical research",
    excerpts: [{ text: "Zingiber officinale was examined.", location: "abstract_sentence:1" }],
  },
  sources: [{
    id: "source-1",
    provider: "pubmed-eutils",
    support_role: "primary_evidence",
    external_identifier: "39900001",
    pmid: "39900001",
    doi: "10.1000/herbwire.2026.1",
    canonical_url: "https://pubmed.ncbi.nlm.nih.gov/39900001/",
    title: "Safety evidence concerning Zingiber officinale",
    authors: ["Amina Researcher"],
    journal: "Journal of Botanical Evidence",
    publication_date: "2026-09-01",
  }],
  review_id: "review-1",
  review_status: "needs_review",
  reviewer_name: null,
  decision_reason: null,
  created_at: "2026-09-02T12:00:00Z",
  reviewed_at: null,
  published_at: null as string | null,
}

const page = (items = [discovery]) => ({
  items,
  total: items.length,
  page: 1,
  page_size: 50,
  pages: 1,
  total_pages: 1,
  filters: {
    plants: [{ value: "Ginger", label: "Ginger (Zingiber officinale Roscoe)" }],
    study_types: [{ value: "Randomized controlled trial", label: "Randomized controlled trial" }],
    evidence_strengths: [{ value: "limited", label: "limited" }],
    publication_years: [{ value: "2026", label: "2026" }],
    research_countries: [{ value: "MX", label: "Mexico" }],
  },
})

function response(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  )
}

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

describe("Milestone 4B discovery UI", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
    vi.stubGlobal("confirm", vi.fn(() => true))
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("keeps the public page empty when only private drafts exist", async () => {
    vi.mocked(fetch).mockImplementation((input) => {
      if (String(input).includes("/api/v1/discoveries")) return response(page([]))
      return response({})
    })
    renderAt("/discoveries")
    expect(screen.getByRole("heading", { name: "Loading published discoveries" })).toBeInTheDocument()
    expect(await screen.findByRole("heading", { name: "No discoveries have been published yet." })).toBeInTheDocument()
    expect(screen.queryByText(discovery.headline)).not.toBeInTheDocument()
  })

  it("renders only API-published discovery cards and provenance", async () => {
    vi.mocked(fetch).mockImplementation(() =>
      response(page([{ ...discovery, status: "published", published_at: "2026-09-02T13:00:00Z" }])),
    )
    renderAt("/discoveries")
    expect(await screen.findByRole("heading", { name: discovery.headline })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Read discovery/i })).toHaveAttribute(
      "href",
      `/discoveries/${discovery.slug}`,
    )
  })

  it("renders the compact discovery archive without promotional sections", async () => {
    vi.mocked(fetch).mockImplementation(() =>
      response({ ...page([{ ...discovery, status: "published", published_at: "2026-09-02T13:00:00Z" }]), total: 22, total_pages: 2, pages: 2 }),
    )
    renderAt("/discoveries")
    expect(await screen.findByRole("heading", { level: 1, name: "TRADITIONAL MEDICINE DISCOVERIES" })).toBeInTheDocument()
    expect(screen.getByText("22 published")).toBeInTheDocument()
    expect(screen.getByLabelText("Search discoveries")).toBeInTheDocument()
    expect(screen.getByRole("navigation", { name: "Discovery archive pagination" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: discovery.headline })).toBeInTheDocument()
    expect(screen.getByRole("contentinfo")).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "New Discoveries" })).not.toBeInTheDocument()
    expect(screen.queryByText(/Evidence-qualified reports linking current research/)).not.toBeInTheDocument()
    expect(screen.queryByText("Editorial standard")).not.toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "A study report is not a prescription." })).not.toBeInTheDocument()
  })

  it("persists public archive search, filters, and pagination in the request URL", async () => {
    vi.mocked(fetch).mockImplementation(() => response({ ...page([{ ...discovery, status: "published", published_at: "2026-09-02T13:00:00Z" }]), total: 13, total_pages: 2, pages: 2 }))
    renderAt("/discoveries")
    await screen.findByRole("heading", { name: discovery.headline })
    fireEvent.change(screen.getByLabelText("Search discoveries"), { target: { value: "ginger" } })
    fireEvent.change(screen.getByLabelText("Filter by plant"), { target: { value: "Ginger" } })
    fireEvent.change(screen.getByLabelText("Filter by study type"), { target: { value: "Randomized controlled trial" } })
    fireEvent.change(screen.getByLabelText("Filter by evidence strength"), { target: { value: "limited" } })
    fireEvent.change(screen.getByLabelText("Filter by publication year"), { target: { value: "2026" } })
    fireEvent.change(screen.getByLabelText("Filter by research country"), { target: { value: "MX" } })
    fireEvent.click(screen.getByRole("button", { name: "Search" }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/query=ginger/), expect.anything()))
    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/plant=Ginger/), expect.anything())
    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/study_type=Randomized/), expect.anything())
    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Next/i }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/page=2/), expect.anything()))
  })

  it("renders a rich published detail with source and plant linkage", async () => {
    const published = {
      ...discovery,
      status: "published",
      published_at: "2026-09-02T13:00:00Z",
      body_blocks: [{
        key: "overview",
        heading: "Overview",
        text: "A source-backed overview long enough for editorial reading.",
        source_ids: ["pubmed:39900001"],
        evidence_locations: ["Abstract"],
      }],
    }
    vi.mocked(fetch).mockImplementation(() => response(published))
    renderAt(`/discoveries/${discovery.slug}`)
    expect(await screen.findByRole("heading", { name: discovery.headline })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Overview" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Ginger/ })).toHaveAttribute("href", "/plants/ginger")
    expect(screen.getByRole("link", { name: new RegExp(discovery.sources[0].title) })).toHaveAttribute("href", discovery.sources[0].canonical_url)
    expect(screen.getByText(/not diagnosis, treatment advice/i)).toBeInTheDocument()
    expect(screen.queryByText("Research geography")).not.toBeInTheDocument()
  })

  it("renders standalone identity and separates botanical from research geography", async () => {
    const published = {
      ...discovery,
      status: "published",
      published_at: "2026-09-03T10:00:00Z",
      linked_plants: [],
      botanical_identity: {
        common_name: "Moringa",
        accepted_scientific_name: "Moringa oleifera Lam.",
        family: "Moringaceae",
        authority_source_id: "powo:584736-1",
        authority_taxon_id: "584736-1",
        authority_url: "https://powo.science.kew.org/taxon/584736-1",
        accepted: true,
      },
      geography: [
        { country_or_region: "India and Pakistan", iso_country_code: null, iso_country_codes: ["IN", "PK"], geography_kind: "botanical_distribution" as const, evidence_type: "native_distribution", source_id: "powo:584736-1", supporting_text_location: "POWO: Distribution", confidence: "high", qualification: "Documented native range.", display_label: "India and Pakistan", map_title: "Documented botanical distribution" },
        { country_or_region: "Mexico", iso_country_code: "MX", iso_country_codes: [], geography_kind: "research_geography" as const, evidence_type: "participant_location", source_id: "pubmed:39900001", supporting_text_location: "Abstract", confidence: "high", qualification: "Participants were reported in Mexico.", display_label: "Mexico", map_title: "Participant location" },
      ],
    }
    vi.mocked(fetch).mockImplementation(() => response(published))
    renderAt(`/discoveries/${discovery.slug}`)
    expect(await screen.findByRole("heading", { name: discovery.headline })).toBeInTheDocument()
    expect(screen.getByText("Verified botanical identity", { exact: false })).toBeInTheDocument()
    expect(screen.getByText("Botanical distribution", { exact: true })).toBeInTheDocument()
    expect(screen.getByText("Research geography", { exact: true })).toBeInTheDocument()
    expect(screen.queryByText("Related plant profile")).not.toBeInTheDocument()
  })

  it("renders the intentional non-public state for a private discovery URL", async () => {
    vi.mocked(fetch).mockImplementation(() => response({ detail: "Discovery not found." }, 404))
    renderAt(`/discoveries/${discovery.slug}`)
    expect(await screen.findByRole("heading", { name: "That discovery is not published." })).toBeInTheDocument()
    expect(screen.queryByText("This discovery is temporarily unavailable.")).not.toBeInTheDocument()
  })

  it("shows the protected review detail and saves hold without publishing", async () => {
    vi.mocked(fetch).mockImplementation((input, init) => {
      const url = String(input)
      if (url.endsWith("/api/v1/auth/session")) {
        return response({ authenticated: true, user: { initials: "HB", label: "Editor", role: "Editor" } })
      }
      if (url.includes("/api/v1/admin/discovery/reviews") && init?.method === "POST") {
        return response({ ...discovery, status: "held", review_status: "held" })
      }
      if (url.includes("/api/v1/admin/discovery/reviews")) return response(page())
      return response({})
    })
    renderAt("/admin/discoveries")

    const workspace = await screen.findByRole("region", { name: "Discovery review workspace" })
    expect(within(workspace).getAllByText(discovery.headline).length).toBeGreaterThan(0)
    expect(within(workspace).getByText(/Zingiber officinale Roscoe/)).toBeInTheDocument()
    expect(within(workspace).getByText("Detail page 1 of 4.")).toBeInTheDocument()
    fireEvent.click(within(workspace).getByRole("button", { name: /4\. Safety, geography, and provenance/ }))
    expect(await within(workspace).findByRole("heading", { name: "Safety, geography, and provenance" })).toHaveFocus()
    expect(within(workspace).getByText(/abstract_sentence:1/)).toBeInTheDocument()
    expect(within(workspace).getByRole("link", { name: discovery.sources[0].title })).toHaveAttribute(
      "href",
      discovery.sources[0].canonical_url,
    )
    expect(within(workspace).getByRole("button", { name: /publish approved version/i })).toBeDisabled()

    fireEvent.change(within(workspace).getByLabelText("Hold or reject reason"), {
      target: { value: "Needs full-method review." },
    })
    fireEvent.click(within(workspace).getByRole("button", { name: "Hold" }))
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("needs_review → held"))
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/hold"),
        expect.objectContaining({ method: "POST" }),
      ),
    )
    expect(await within(workspace).findByRole("alert")).toHaveTextContent("held")
  })

  it("labels and filters the final eight review batch", async () => {
    const finalDraft = {
      ...discovery,
      id: "final-eight-draft",
      evidence_package: {
        ...discovery.evidence_package,
        batch_id: "milestone-4c-final-eight",
      },
    }
    vi.mocked(fetch).mockImplementation((input) => {
      const url = String(input)
      if (url.endsWith("/api/v1/auth/session")) {
        return response({ authenticated: true, user: { initials: "HB", label: "Editor", role: "Editor" } })
      }
      if (url.includes("/api/v1/admin/discovery/reviews")) return response(page([finalDraft]))
      return response({})
    })
    renderAt("/admin/discoveries")

    const workspace = await screen.findByRole("region", { name: "Discovery review workspace" })
    expect(within(workspace).getByText(/final eight/)).toBeInTheDocument()
    fireEvent.change(within(workspace).getByLabelText("Filter discovery batch"), {
      target: { value: "milestone-4c-final-eight" },
    })
    expect(within(workspace).getByText(/final eight/)).toBeInTheDocument()
  })

  it("renders stage failures and submits only bounded PubMed trigger fields", async () => {
    const run = {
      id: "run-1",
      pipeline_type: "pubmed_discovery_review",
      trigger: "manual_admin",
      provider: "pubmed",
      idempotency_key: "opaque",
      status: "failed",
      current_stage: "collect",
      summary: {},
      started_at: "2026-09-02T12:00:00Z",
      finished_at: "2026-09-02T12:00:01Z",
      stages: [{
        name: "collect",
        status: "failed",
        attempt: 1,
        duration_ms: 12,
        input_count: 0,
        output_count: 0,
        input_refs: [],
        output_refs: [],
        error_code: "pubmed_transport_error",
        error_message: "PubMed timed out safely.",
      }],
    }
    vi.mocked(fetch).mockImplementation((input, init) => {
      const url = String(input)
      if (url.endsWith("/api/v1/auth/session")) {
        return response({ authenticated: true, user: { initials: "HB", label: "Editor", role: "Editor" } })
      }
      if (url.endsWith("/api/v1/admin/pipeline/runs")) return response([run])
      if (url.endsWith("/api/v1/admin/discovery/runs") && init?.method === "POST") {
        return response({ ...run, status: "succeeded" })
      }
      return response({})
    })
    renderAt("/admin/runs")

    expect(await screen.findByText(/pubmed_transport_error: PubMed timed out safely/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Maximum PubMed records"), { target: { value: "3" } })
    fireEvent.click(screen.getByRole("button", { name: "Run once" }))
    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(([input]) =>
        String(input).endsWith("/api/v1/admin/discovery/runs"),
      )
      expect(JSON.parse(String(call?.[1]?.body))).toMatchObject({
        source: "pubmed",
        max_records: 3,
      })
      expect(JSON.parse(String(call?.[1]?.body))).not.toHaveProperty("url")
    })
  })

  it("renders public error recovery and discovery queue pagination", async () => {
    let publicFailures = 1
    const articles = Array.from({ length: 7 }, (_, index) => ({
      ...discovery,
      id: `discovery-${index + 1}`,
      headline: `Discovery draft ${index + 1}`,
    }))
    vi.mocked(fetch).mockImplementation((input) => {
      const url = String(input)
      if (url.endsWith("/api/v1/auth/session")) {
        return response({ authenticated: true, user: { initials: "HB", label: "Editor", role: "Editor" } })
      }
      if (url.includes("/api/v1/admin/discovery/reviews")) return response(page(articles))
      if (url.includes("/api/v1/discoveries")) {
        if (publicFailures) {
          publicFailures -= 1
          return response({ detail: "Unavailable" }, 503)
        }
        return response(page([]))
      }
      return response({})
    })

    const publicView = renderAt("/discoveries")
    expect(await screen.findByRole("heading", { name: "Discoveries are temporarily unavailable." })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Try again" }))
    expect(await screen.findByRole("heading", { name: "No discoveries have been published yet." })).toBeInTheDocument()
    publicView.unmount()

    renderAt("/admin/discoveries")
    const workspace = await screen.findByRole("region", { name: "Discovery review workspace" })
    expect(within(workspace).getByText("Page 1 of 2")).toBeInTheDocument()
    expect(within(workspace).queryByText("Discovery draft 7")).not.toBeInTheDocument()
    fireEvent.click(within(workspace).getByRole("button", { name: /3\. Findings and evidence/ }))
    expect(within(workspace).getByText("Detail page 3 of 4.")).toBeInTheDocument()
    fireEvent.click(within(workspace).getByRole("button", { name: "Next discovery page" }))
    expect(await within(workspace).findAllByText("Discovery draft 7")).not.toHaveLength(0)
    expect(within(workspace).getByText("Page 2 of 2")).toBeInTheDocument()
    expect(within(workspace).getByText("Detail page 3 of 4.")).toBeInTheDocument()
    fireEvent.click(within(workspace).getByRole("button", { name: /Discovery draft 7/i }))
    expect(within(workspace).getByText("Detail page 1 of 4.")).toBeInTheDocument()
  })})
