import "@testing-library/jest-dom/vitest"
import { act, fireEvent, render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import type { ApiPublicDiscoveryArticle } from "../../api/discoveries"
import { HomeDiscoveryCarousel } from "./HomeDiscoveryCarousel"
import { presentationExcerpt } from "./carouselExcerpt"

vi.setConfig({ testTimeout: 15_000 })

function article(index: number): ApiPublicDiscoveryArticle {
  return {
    id: `article-${index}`,
    slug: `article-${index}`,
    headline: `Article ${index}`,
    standfirst: `Article ${index} standfirst`,
    body_blocks: [],
    limitations: [],
    safety_context: "Safety context",
    cannot_conclude: [],
    version: 1,
    article_type: "Review",
    research_date: "2026-09-01",
    research_question: null,
    research_context: null,
    study_design: null,
    evidence_base: null,
    intervention: null,
    comparator: null,
    main_findings: [],
    category: "research",
    evidence_strength: "moderate",
    evidence_strength_rationale: null,
    why_matters: null,
    practical_interpretation: null,
    section_sources: {},
    hero_image: { local_path: `/media/article-${index}.jpg`, alt_text: `Article ${index} cover` },
    geography: [],
    linked_plants: [],
    botanical_identity: null,
    sources: [{ id: `source-${index}`, provider: "pubmed", support_role: "primary_evidence", external_identifier: String(index), pmid: String(index), doi: null, canonical_url: "https://pubmed.ncbi.nlm.nih.gov/", title: `Source ${index}`, authors: [], journal: "Journal", publication_date: "2026-09-01" }],
    created_at: "2026-09-01T00:00:00Z",
    published_at: "2026-09-01T00:00:00Z",
  }
}

function carousel(items = [article(1), article(2), article(3)]) {
  return <MemoryRouter><HomeDiscoveryCarousel items={items} /></MemoryRouter>
}

describe("carousel presentation excerpt", () => {
  it("uses a suitably short first meaningful sentence", () => {
    const sentence =
      "A carefully qualified first sentence explains the central finding without overwhelming the editorial image."
    expect(
      presentationExcerpt(
        sentence + " A second sentence retains the full stored deck outside this view.",
        "A distinct headline",
      ),
    ).toBe(sentence)
  })

  it("truncates at a word boundary without changing the stored source text", () => {
    const deck =
      "This source-led description contains deliberately extended context so the carousel can create a balanced presentation excerpt while the canonical article deck remains entirely unchanged in the API response."
    const original = deck
    const excerpt = presentationExcerpt(deck, "A distinct headline", 120)

    expect(excerpt.length).toBeLessThanOrEqual(121)
    expect(excerpt).toMatch(/\u2026$/)
    expect(excerpt).not.toMatch(/\s\u2026$/)
    expect(deck).toBe(original)
  })

  it("does not repeat a deck that is identical to the headline", () => {
    expect(presentationExcerpt("Same words", "Same words")).toBe("")
  })
})

describe("home discovery carousel", () => {
  it("renders three total slides with linked title and image, navigation, and image fallback", () => {
    render(carousel())
    const region = screen.getByRole("region", { name: "Latest published discoveries" })
    expect(within(region).getByText("01 / 03")).toBeInTheDocument()
    expect(within(region).getByRole("link", { name: "Article 1" })).toHaveAttribute("href", "/discoveries/article-1")
    expect(within(region).getByRole("link", { name: "Read discovery: Article 1" })).toHaveAttribute("href", "/discoveries/article-1")
    fireEvent.error(within(region).getByRole("img", { name: "Article 1 cover" }))
    expect(within(region).getByText("Image temporarily unavailable")).toBeInTheDocument()
    fireEvent.click(within(region).getByRole("button", { name: "Show previous discovery" }))
    expect(within(region).getByRole("heading", { name: "Article 3" })).toBeInTheDocument()
  })

  it("pauses autoplay on hover and supports swipe navigation", async () => {
    vi.useFakeTimers()
    render(carousel())
    const region = screen.getByRole("region", { name: "Latest published discoveries" })
    fireEvent.mouseEnter(region)
    await act(async () => { await vi.advanceTimersByTimeAsync(6000) })
    expect(within(region).getByRole("heading", { name: "Article 1" })).toBeInTheDocument()
    fireEvent.mouseLeave(region)
    fireEvent.touchStart(region, { touches: [{ clientX: 200 }] })
    fireEvent.touchEnd(region, { changedTouches: [{ clientX: 100 }] })
    expect(within(region).getByRole("heading", { name: "Article 2" })).toBeInTheDocument()
    vi.useRealTimers()
  })

  it("normalizes the active index safely when item count changes", () => {
    const { rerender } = render(carousel())
    fireEvent.click(screen.getByRole("button", { name: "Show previous discovery" }))
    expect(screen.getByRole("heading", { name: "Article 3" })).toBeInTheDocument()
    rerender(carousel([article(1)]))
    expect(screen.getByRole("heading", { name: "Article 1" })).toBeInTheDocument()
    expect(screen.getByText("01 / 01")).toBeInTheDocument()
  })
})
