import "@testing-library/jest-dom/vitest"
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"

vi.setConfig({ testTimeout: 15_000 })

const plant = (index: number) => ({ id: `plant-${index}`, slug: `plant-${index}`, accepted_scientific_name: `Planta test ${index}`, botanical_author: "L.", taxon_identifier: `powo:${index}`, known_synonyms: [], display_common_name: `Plant ${index}`, family_name: "Lamiaceae", diversity_tags: ["Europe"], summary: `Reviewed plant summary ${index}.`, status: "published", hero_image: { local_path: `/media/plants/plant-${index}.jpg`, alt_text: `Plant ${index}` }, published_at: "2026-09-02T12:00:00Z", source_count: 3, growth_form: "herb", biome: "temperate", distribution_summary: "Europe", readiness_status: "ready_for_review", version: 1 })
const discovery = (index: number) => ({ id: `discovery-${index}`, slug: `discovery-${index}`, headline: `Discovery headline ${index}`, standfirst: `Evidence-qualified deck ${index}.`, body_blocks: [], limitations: [], safety_context: "Safety context.", cannot_conclude: [], version: 1, article_type: "Systematic review", research_date: "2026-09-02", research_question: null, research_context: null, study_design: null, evidence_base: null, intervention: null, comparator: null, main_findings: [], evidence_strength: "moderate", evidence_strength_rationale: null, why_matters: null, practical_interpretation: null, section_sources: {}, hero_image: { local_path: `/media/discoveries/discovery-${index}.jpg`, alt_text: `Discovery ${index}` }, geography: [], linked_plants: [], botanical_identity: { common_name: `Discovery plant ${index}`, accepted_scientific_name: `Discoveria ${index}`, family: "Testaceae", authority_source_id: "powo", authority_taxon_id: String(index), authority_url: "https://powo.science.kew.org/", accepted: true }, category: "research", sources: [{ id: `source-${index}`, provider: "pubmed", support_role: "primary_research", external_identifier: String(10000000 + index), pmid: String(10000000 + index), doi: `10.1000/${index}`, canonical_url: `https://pubmed.ncbi.nlm.nih.gov/${10000000 + index}/`, title: `Source ${index}`, authors: [], journal: "Journal", publication_date: `2026-0${Math.min(index, 9)}-01` }], created_at: "2026-09-02T12:00:00Z", published_at: `2026-09-0${Math.min(index, 9)}T12:00:00Z` })

const discoveries = [
  { ...discovery(1), slug: "amla-36934568-cardiometabolic-meta-analysis", headline: "Amla review reports cardiometabolic marker changes from only five small trials" },
  { ...discovery(2), slug: "st-johns-wort-36246064-evidence-interactions-review", headline: "St John's wort review places clinical evidence beside consequential interaction risk" },
  ...Array.from({ length: 5 }, (_, index) => discovery(index + 3)),
]
const plants = Array.from({ length: 3 }, (_, index) => plant(index + 1))
const contentPage = { summary: { total_content: 67, published_plants: 30, published_discoveries: 30, published_materials: 7, source_records: 150, provenance_relationships: 245, needs_review: 0 }, items: [{ id: "plant-1", title: "Plant 1", content_type: "plant_profile", content_type_label: "Plant Profile", status: "published", timestamp: "2026-09-02T12:00:00Z", plant_identity: "Planta test 1", source_count: 3, origin: "curated corpus", public_path: "/plants/plant-1", editorial_path: "/admin/reviews", pmid: null }], total: 67, page: 1, page_size: 10, total_pages: 7, statuses: ["published"] }
const materialRecords = [
  ["palm-fibre-basketry-morocco", "Palm fibres, coiled form: reading Moroccan basketry closely", "Fibres", "Morocco", "/media/materials/moroccan-basketry.jpg", "Colourful handmade palm-fibre baskets displayed in a market in Marrakesh, Morocco"],
  ["apothecary-glass-storage-vessels", "Clear evidence: why apothecaries trusted glass vessels", "Glass", "Europe and North America", "/media/materials/apothecary-glass.jpg", "A group of historic brown and clear glass apothecary vials"],
  ["washi-plant-fibres-handmade-paper", "Long fibres, quiet strength: how washi holds together", "Paper", "Japan", "/media/materials/washi-paper.jpg", "Sheets of pale handmade Sugihara washi paper arranged together"],
  ["indigo-plant-dyes-colour-craft", "Colour from a vat: understanding plant-derived indigo", "Pigments & Dyes", "Documented practices in Asia", "/media/materials/natural-indigo.jpg", "Blue indigo-dyed cloth being lifted from a dye vat by hand"],
  ["cork-oak-bark-harvest-material", "The bark that returns: cork harvest as a material cycle", "Cork", "Western Mediterranean", "/media/materials/cork-harvest.jpg", "A cork oak trunk during careful bark harvesting near Aracena, Spain"],
  ["wood-grain-carving-hand-tools", "Following the grain: wood, tools and the discipline of carving", "Wood", "Konjic, Bosnia and Herzegovina", "/media/materials/woodcarver.jpg", "A master woodcarver working carefully with hand tools in an Uzbekistan workshop"],
  ["zlakusa-hand-wheel-pottery-vessels", "Clay, calcite and fire: the working vessels of Zlakusa", "Clay & Glass", "Zlakusa, Serbia", "/media/materials/zlakusa-pottery.jpg", "Potters from Zlakusa shaping traditional vessels in a workshop"],
] as const
const materials = materialRecords.map(([slug, title, category, geography, image, alt], index) => ({ id: `material-${index + 1}`, slug, title, deck: `Existing source-led material story about ${category.toLowerCase()} and patient handwork.`, category, material_labels: [category], geography_label: geography, reading_time_minutes: 7, featured: index === 0, published_at: `2026-09-03T0${9 - index}:00:00Z`, hero_media: { local_path: image, source_page: "https://commons.wikimedia.org/", direct_asset_url: "https://upload.wikimedia.org/example.jpg", creator: "Contributor", title, attribution: "Contributor, licensed media", license: "CC BY-SA 4.0", license_url: "https://creativecommons.org/licenses/by-sa/4.0/", checksum_sha256: "a".repeat(64), alt_text: alt } }))
const material = materials[0]
const homepageMaterial = materials[5]
const materialPage = { items: materials, total: 7, page: 1, page_size: 12, total_pages: 1, categories: ["Clay & Glass", "Cork", "Fibres", "Glass", "Paper", "Pigments & Dyes", "Wood"] }
const materialDetail = { ...material, content_version: 1, sections: Array.from({ length: 6 }, (_, index) => ({ key: "section-" + index, heading: "Material section " + (index + 1), text: "A substantial source-led explanation of the material and documented making practice.", source_ids: ["unesco:test"] })), sources: [{ id: "source-1", source_name: "UNESCO", title: "Institutional source", source_type: "cultural_heritage", external_identifier: "test", canonical_url: "https://ich.unesco.org/", supported_sections: ["section-0"] }], related: [] }
const sourcePage = { items: [{ id: "source-1", source_name: "PubMed", source_type: "research", authoritative_domain: "pubmed.ncbi.nlm.nih.gov", external_identifier: "12345678", doi: "10.1000/source", title: "Genuine indexed source", publisher: "Journal", provenance_roles: ["primary_research"], linked_content_count: 1, associated_content: [{ content_id: "discovery-1", content_type: "discovery", title: "Discovery headline 1", internal_path: "/discoveries/discovery-1" }], created_at: "2026-09-02T12:00:00Z", external_url: "https://pubmed.ncbi.nlm.nih.gov/12345678/" }], total: 150, page: 1, page_size: 12, total_pages: 13, source_count: 7, source_record_count: 150, source_types: ["research"] }

function response(body: unknown, status = 200) { return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })) }
function renderAt(path: string) { return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>) }

function installApi(materialsStatus = 200) {
  vi.mocked(fetch).mockImplementation((input) => {
    const url = String(input)
    if (url.endsWith("/api/v1/auth/session")) return response({ authenticated: true, user: { initials: "HB", label: "Local admin", role: "Editor" } })
    if (url.includes("/api/v1/admin/catalog/content")) return response(contentPage)
    if (url.includes("/api/v1/admin/catalog/sources")) return response(sourcePage)
    if (url.endsWith("/api/v1/admin/agent-performance")) return response({ total_runs: 0, succeeded_runs: 0, failed_runs: 0, held_runs: 0, auto_published: 0, last_execution: null, stages: [] })
    if (url.includes("/api/v1/materials/")) return response(materialDetail)
    if (url.includes("/api/v1/materials")) return response(materialPage, materialsStatus)
    if (url.includes("/api/v1/discoveries")) return response({ items: discoveries, total: 30, page: 1, page_size: 12, pages: 3, total_pages: 3, filters: { plants: [], study_types: [], evidence_strengths: [], publication_years: [], research_countries: [] } })
    if (url.includes("/api/v1/plants")) return response({ items: plants, total: 30, page: 1, page_size: 50, pages: 1 })
    return response({})
  })
}

describe("demo frontend enhancement", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
    installApi()
  })
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

  it("renders the filtered three-slide hero, homepage sections in order, plants, and navigation", async () => {
    renderAt("/")
    expect(
      await screen.findByRole(
        "heading",
        { name: "St John's wort review places clinical evidence beside consequential interaction risk" },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument()
    const carousel = screen.getByRole("region", { name: "Latest published discoveries" })
    expect(within(carousel).getByRole("button", { name: "Show previous discovery" })).toBeInTheDocument()
    expect(within(carousel).getByText("01 / 03")).toBeInTheDocument()
    expect(within(carousel).queryByText(/Amla review reports/i)).not.toBeInTheDocument()
    for (const index of [5, 6, 7]) expect(screen.getByRole("link", { name: new RegExp(`Discovery headline ${index}`) })).toHaveAttribute("href", `/discoveries/discovery-${index}`)
    const materialsHeading = screen.getByRole("heading", { name: "Materials shaped by patient hands" })
    expect(screen.getByRole("link", { name: /Explore Materials & Craft/i })).toHaveAttribute("href", "/materials-and-craft")
    expect(screen.getByRole("heading", { name: homepageMaterial.title })).toBeInTheDocument()
    expect(screen.getAllByRole("link", { name: new RegExp(homepageMaterial.title) }).some((link) => link.getAttribute("href") === `/materials-and-craft/${homepageMaterial.slug}`)).toBe(true)
    const latestHeading = screen.getByRole("heading", { name: "New evidence, carefully read" })
    const plantsHeading = screen.getByRole("heading", { name: "Reviewed medicinal plants" })
    expect(latestHeading.compareDocumentPosition(materialsHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(materialsHeading.compareDocumentPosition(plantsHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole("link", { name: /More discoveries/i })).toHaveAttribute("href", "/discoveries")
    expect(screen.getByRole("link", { name: /More medicinal plants/i })).toHaveAttribute("href", "/plants")
    expect(screen.getAllByText(/Plant [123]/).length).toBeGreaterThanOrEqual(3)
    expect(screen.queryByText("Medicinal knowledge is a world story.")).not.toBeInTheDocument()
    const nav = screen.getByRole("navigation", { name: "Primary navigation" })
    expect(within(nav).getByRole("link", { name: "Materials & Craft" })).toHaveAttribute("href", "/materials-and-craft")
    expect(within(nav).getByRole("link", { name: "The Field Cabinet" })).toHaveAttribute("href", "/field-cabinet")
  })

  it("advances every six seconds, resets manually, and pauses while focused", async () => {
    vi.useFakeTimers()
    renderAt("/")
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(screen.getByRole("heading", { name: /St John's wort review places/ })).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(6000) })
    expect(screen.getByRole("heading", { name: "Discovery headline 3" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Show next discovery" }))
    expect(screen.getByRole("heading", { name: "Discovery headline 4" })).toBeInTheDocument()
    screen.getByRole("link", { name: "Discovery headline 4" }).focus()
    await act(async () => { await vi.advanceTimersByTimeAsync(6000) })
    expect(screen.getByRole("heading", { name: "Discovery headline 4" })).toBeInTheDocument()
  })

  it("disables forced carousel advancement for reduced-motion users", async () => {
    vi.useFakeTimers()
    vi.mocked(matchMedia).mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList)
    renderAt("/")
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(screen.getByRole("heading", { name: /St John's wort review places/ })).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(6000) })
    expect(screen.getByRole("heading", { name: /St John's wort review places/ })).toBeInTheDocument()
  })

  it("keeps the homepage-excluded Amla article available in the Discovery archive", async () => {
    renderAt("/discoveries")
    expect(await screen.findByRole("link", { name: /Amla review reports cardiometabolic/i })).toHaveAttribute("href", "/discoveries/amla-36934568-cardiometabolic-meta-analysis")
  })

  it("keeps the rest of the homepage available when the Materials API fails", async () => {
    installApi(503)
    renderAt("/")
    expect(await screen.findByRole("heading", { name: /St John's wort review places/ })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "New evidence, carefully read" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Reviewed medicinal plants" })).toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent("material stories are temporarily unavailable")
  })

  it("renders the real Materials collection and detail route in the shared shell", async () => {
    const materials = renderAt("/materials-and-craft")
    expect(await screen.findByRole("heading", { name: "Made by hand, shaped by the living world." })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Explore the collection" })).toBeInTheDocument()
    expect(screen.getAllByRole("link", { name: /Palm fibres, coiled form/i }).length).toBeGreaterThan(0)
    materials.unmount()
    renderAt(`/materials-and-craft/${material.slug}`)
    expect(await screen.findByRole("heading", { name: material.title })).toBeInTheDocument()
    expect(screen.getByText("Source provenance")).toBeInTheDocument()
  })

  it("renders truthful dashboard, the complete agent roster, and source catalogue", async () => {
    const dashboard = renderAt("/admin")
    expect(await screen.findByRole("heading", { name: "Content operations" })).toBeInTheDocument()
    expect(screen.getByText("67 content records")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Next/i }))
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("page=2"))).toBe(true))
    dashboard.unmount()
    renderAt("/admin/performance")
    expect(await screen.findByText("DEMO-DERIVED PERFORMANCE MODEL")).toBeInTheDocument()
    expect(screen.getByText(/not live production telemetry/i)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Active discovery agents" })).toBeInTheDocument()
    expect(document.querySelectorAll('[data-agent-status="enabled"]')).toHaveLength(8)
    expect(document.querySelectorAll('[data-agent-status="planned"]')).toHaveLength(4)
    expect(screen.getAllByText("Editorial Queue Agent").length).toBeGreaterThan(0)
    expect(vi.mocked(fetch).mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true)
  })

  it("renders genuine source metadata and links without sensitive fields", async () => {
    renderAt("/admin/sources")
    expect(await screen.findByRole("heading", { name: "Source records" })).toBeInTheDocument()
    expect(screen.getByText("Genuine indexed source")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Open external source/i })).toHaveAttribute("href", "https://pubmed.ncbi.nlm.nih.gov/12345678/")
    expect(document.body.textContent?.toLowerCase()).not.toContain("database_url")
  })
})
