import { describe, expect, it } from "vitest"

import { presentationExcerpt } from "./carouselExcerpt"

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