import "@testing-library/jest-dom/vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import App from "./App"

function response(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  )
}

function installApi(plantRun: unknown = null, discoveryRun: unknown = null) {
  vi.mocked(fetch).mockImplementation((input) => {
    const url = String(input)
    if (url.endsWith("/api/v1/auth/session")) {
      return response({
        authenticated: true,
        user: { initials: "HB", label: "Local admin", role: "Editor" },
      })
    }
    if (url.includes("/preview")) {
      return response({ can_start: true, unavailable_reason: null, active_pipeline: null })
    }
    if (url.includes("/plant-pipeline/runs/")) return response(plantRun)
    if (url.includes("/discovery-pipeline/runs/")) return response(discoveryRun)
    return response(null)
  })
}
describe("Plant Pipeline editorial page", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn()))
  afterEach(() => {
    window.sessionStorage.clear()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("renders navigation, bounded selector, preview, and singular/plural actions", async () => {
    installApi()
    render(
      <MemoryRouter initialEntries={["/admin/pipelines"]}>
        <App />
      </MemoryRouter>,
    )

    expect(
      await screen.findByRole(
        "heading", { name: "Pipelines" }, { timeout: 5000 },
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Pipelines" })).toHaveAttribute(
      "href",
      "/admin/pipelines",
    )
    expect(screen.getByRole("heading", { name: "Plants pipeline" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Discoveries pipeline" })).toBeInTheDocument()
    expect(screen.getByRole("region", { name: "Plants pipeline results" })).toBeEmptyDOMElement()
    expect(screen.getByRole("region", { name: "Discoveries pipeline results" })).toBeEmptyDOMElement()
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Run the Discoveries pipeline" }),
      ).toBeEnabled(),
    )
    expect(screen.queryByText("Next eligible candidates")).not.toBeInTheDocument()
    expect(
      screen.queryByText("No hosted LLM, paid API, automatic approval, or automatic publication is used."),
    ).not.toBeInTheDocument()
    const selector = screen.getByRole("spinbutton", { name: "Profiles to generate" })
    expect(selector).toHaveValue(1)
    expect(selector).toHaveAttribute("min", "1")
    expect(selector).toHaveAttribute("max", "10")
    expect(screen.getByRole("button", { name: "Run the Plants pipeline" })).toBeEnabled()
    expect(screen.queryByText(/Achillea millefolium/)).not.toBeInTheDocument()
    expect(screen.getByRole("checkbox", { name: "All available Plant profiles" })).toBeEnabled()

    fireEvent.change(selector, { target: { value: "3" } })
    await waitFor(() => expect(screen.getByRole("button", { name: "Run the Plants pipeline" })).toBeEnabled())
    expect(screen.getAllByText(/completes before the next begins/i)).toHaveLength(2)
  }, 10_000)

  it("recovers only the session-scoped run and renders title plus status", async () => {
    window.sessionStorage.setItem("herbwire.pipeline.plants.run", "run-1")
    installApi({
      id: "run-1",
      status: "failed",
      items: [{
        id: "item-1",
        title: "Yarrow",
        status: "failed",
        editorial_status: "needs_review",
        plant_profile_id: "plant-1",
        review_id: "review-1",
      }],
    })
    render(
      <MemoryRouter initialEntries={["/admin/pipelines"]}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByRole("link", { name: "Yarrow" })).toHaveAttribute(
      "href",
      "/admin/reviews?review=review-1",
    )
    expect(screen.getByText("Failed")).toBeInTheDocument()
    expect(screen.queryByText("Editorial QA")).not.toBeInTheDocument()
    expect(screen.queryByText(/taxonomy verified/i)).not.toBeInTheDocument()
    expect(screen.queryByText("Review draft")).not.toBeInTheDocument()
  })
  it("redirects the old route and renders only a session-scoped Discovery result", async () => {
    window.sessionStorage.setItem("herbwire.pipeline.discoveries.run", "discovery-run-1")
    installApi(null, {
      id: "discovery-run-1",
      status: "succeeded",
      items: [{
        id: "discovery-item-1",
        title: "Cocoa study reports a bounded cardiovascular result",
        status: "succeeded",
        editorial_status: "needs_review",
        discovery_article_id: "article-1",
        review_id: "review-1",
      }],
    })
    render(
      <MemoryRouter initialEntries={["/admin/plant-pipeline"]}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByRole("heading", { name: "Pipelines" })).toBeInTheDocument()
    expect(
      await screen.findByRole("link", {
        name: "Cocoa study reports a bounded cardiovascular result",
      }),
    ).toHaveAttribute("href", "/admin/discoveries?article=article-1")
    expect(screen.queryByText("Latest result")).not.toBeInTheDocument()
  })
})
