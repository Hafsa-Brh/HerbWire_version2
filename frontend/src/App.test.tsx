import "@testing-library/jest-dom/vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import App from "./App"

function createDeferredResponse() {
  let resolve!: (value: Response) => void
  const promise = new Promise<Response>((innerResolve) => {
    resolve = innerResolve
  })

  return { promise, resolve }
}

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("shows a loading state before the health request resolves", () => {
    const deferred = createDeferredResponse()
    vi.mocked(fetch).mockReturnValue(deferred.promise)

    render(<App />)

    expect(screen.getByRole("status")).toHaveTextContent(
      "Checking backend and database connectivity",
    )
  })

  it("shows the connected state and backend version", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ok",
          service: "herbwire-api",
          version: "0.1.0",
          database: "connected",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    )

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText("0.1.0")).toBeInTheDocument()
    })
    expect(screen.getByText("connected", { selector: "dd" })).toBeInTheDocument()
  })

  it("shows the degraded state when the backend reports a database disconnect", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "degraded",
          service: "herbwire-api",
          version: "0.1.0",
          database: "disconnected",
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      ),
    )

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText(/database connection is unavailable/i)).toBeInTheDocument()
    })
    expect(screen.getByText("disconnected", { selector: "dd" })).toBeInTheDocument()
  })

  it("shows the unreachable state when the backend cannot be reached", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("network down"))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText(/backend is unavailable from the frontend/i)).toBeInTheDocument()
    })
  })

  it("requests the documented default backend health endpoint", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ok",
          service: "herbwire-api",
          version: "0.1.0",
          database: "connected",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    )

    render(<App />)

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(1)
    })
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/health",
      expect.objectContaining({
        headers: { Accept: "application/json" },
      }),
    )
  })
})
