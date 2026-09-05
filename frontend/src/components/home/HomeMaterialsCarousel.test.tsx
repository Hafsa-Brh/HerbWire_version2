import "@testing-library/jest-dom/vitest"
import { act, fireEvent, render, screen, within } from "@testing-library/react"
import type { ComponentProps } from "react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { MaterialSummary } from "../../api/materials"
import { HomeMaterialsCarousel } from "./HomeMaterialsCarousel"

vi.setConfig({ testTimeout: 15_000 })

const materialRecords = [
  ["palm-fibre-basketry-morocco", "Palm fibres, coiled form: reading Moroccan basketry closely", "Fibres", "Morocco", "/media/materials/moroccan-basketry.jpg", "Colourful handmade palm-fibre baskets displayed in a market in Marrakesh, Morocco"],
  ["apothecary-glass-storage-vessels", "Clear evidence: why apothecaries trusted glass vessels", "Glass", "Europe and North America", "/media/materials/apothecary-glass.jpg", "A group of historic brown and clear glass apothecary vials"],
  ["washi-plant-fibres-handmade-paper", "Long fibres, quiet strength: how washi holds together", "Paper", "Japan", "/media/materials/washi-paper.jpg", "Sheets of pale handmade Sugihara washi paper arranged together"],
  ["indigo-plant-dyes-colour-craft", "Colour from a vat: understanding plant-derived indigo", "Pigments & Dyes", "Documented practices in Asia", "/media/materials/natural-indigo.jpg", "Blue indigo-dyed cloth being lifted from a dye vat by hand"],
  ["cork-oak-bark-harvest-material", "The bark that returns: cork harvest as a material cycle", "Cork", "Western Mediterranean", "/media/materials/cork-harvest.jpg", "A cork oak trunk during careful bark harvesting near Aracena, Spain"],
  ["wood-grain-carving-hand-tools", "Following the grain: wood, tools and the discipline of carving", "Wood", "Konjic, Bosnia and Herzegovina", "/media/materials/woodcarver.jpg", "A master woodcarver working carefully with hand tools in an Uzbekistan workshop"],
  ["zlakusa-hand-wheel-pottery-vessels", "Clay, calcite and fire: the working vessels of Zlakusa", "Clay & Glass", "Zlakusa, Serbia", "/media/materials/zlakusa-pottery.jpg", "Potters from Zlakusa shaping traditional vessels in a workshop"],
] as const

const items: MaterialSummary[] = materialRecords.map(([slug, title, category, geography, localPath, altText], index) => ({
  id: `material-${index + 1}`,
  slug,
  title,
  deck: `An existing source-led story about ${category.toLowerCase()} and patient handwork.`,
  category,
  material_labels: [category],
  geography_label: geography,
  reading_time_minutes: 7,
  featured: index === 0,
  published_at: "2026-09-03T09:00:00Z",
  hero_media: { local_path: localPath, alt_text: altText, source_page: "https://commons.wikimedia.org/", direct_asset_url: "https://upload.wikimedia.org/example.jpg", creator: "Contributor", title, attribution: "Licensed media", license: "CC BY-SA 4.0", license_url: "https://creativecommons.org/licenses/by-sa/4.0/", checksum_sha256: "a".repeat(64) },
}))

function renderCarousel(props: Partial<ComponentProps<typeof HomeMaterialsCarousel>> = {}) {
  return render(<MemoryRouter><HomeMaterialsCarousel items={items} {...props} /></MemoryRouter>)
}

describe("home materials carousel", () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it("renders the API-backed order, links, accessible images, previews, and seven-story counter", () => {
    renderCarousel()
    const region = screen.getByRole("region", { name: "Featured material stories" })
    expect(screen.getByRole("heading", { name: "Materials shaped by patient hands" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Explore Materials & Craft/i })).toHaveAttribute("href", "/materials-and-craft")
    expect(within(region).getByRole("heading", { name: items[0].title })).toBeInTheDocument()
    expect(within(region).getByText("01 / 07")).toBeInTheDocument()
    expect(within(region).getByRole("img", { name: items[0].hero_media.alt_text })).toBeInTheDocument()
    expect(within(region).getByRole("link", { name: `Read previous material story: ${items[6].title}` })).toHaveAttribute("href", `/materials-and-craft/${items[6].slug}`)
    expect(within(region).getByRole("link", { name: `Read next material story: ${items[1].title}` })).toHaveAttribute("href", `/materials-and-craft/${items[1].slug}`)
  })

  it("moves next and previous with safe wrapping and updates counter and progress", () => {
    renderCarousel()
    const next = screen.getByRole("button", { name: "Show next material story" })
    fireEvent.click(next)
    expect(screen.getByRole("heading", { name: items[1].title })).toBeInTheDocument()
    expect(screen.getByText("02 / 07")).toBeInTheDocument()
    expect(screen.getByRole("progressbar", { name: "Material stories progress" })).toHaveAttribute("aria-valuenow", "2")
    fireEvent.click(screen.getByRole("button", { name: "Show previous material story" }))
    fireEvent.click(screen.getByRole("button", { name: "Show previous material story" }))
    expect(screen.getByRole("heading", { name: items[6].title })).toBeInTheDocument()
    expect(screen.getByText("07 / 07")).toBeInTheDocument()
    expect(screen.getByRole("progressbar", { name: "Material stories progress" })).toHaveAttribute("aria-valuenow", "7")
    expect(screen.getByText(`Material story 7 of 7: ${items[6].title}`)).toBeInTheDocument()
  })

  it("advances every three seconds and pauses for hover and keyboard focus", async () => {
    vi.useFakeTimers()
    renderCarousel()
    const region = screen.getByRole("region", { name: "Featured material stories" })
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(screen.getByRole("heading", { name: items[1].title })).toBeInTheDocument()
    fireEvent.mouseEnter(region)
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(screen.getByRole("heading", { name: items[1].title })).toBeInTheDocument()
    fireEvent.mouseLeave(region)
    screen.getByRole("button", { name: "Show next material story" }).focus()
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(screen.getByRole("heading", { name: items[1].title })).toBeInTheDocument()
  })

  it("does not autoplay for reduced-motion users", async () => {
    vi.useFakeTimers()
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
    renderCarousel()
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(screen.getByRole("heading", { name: items[0].title })).toBeInTheDocument()
  })

  it("renders isolated loading, empty, and failure states", () => {
    const loading = renderCarousel({ items: [], isLoading: true })
    expect(screen.getByRole("status")).toHaveTextContent("Opening the material stories")
    loading.unmount()
    const retry = vi.fn()
    const failed = renderCarousel({ items: [], error: new Error("offline"), onRetry: retry })
    fireEvent.click(screen.getByRole("button", { name: "Try again" }))
    expect(retry).toHaveBeenCalledOnce()
    failed.unmount()
    renderCarousel({ items: [] })
    expect(screen.getByRole("status")).toHaveTextContent("No published material stories")
  })
})
