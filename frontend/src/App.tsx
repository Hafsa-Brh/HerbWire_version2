import { useEffect, useState } from "react"

import { fetchHealth, getApiBaseUrl, type ApiHealthResponse } from "./api/health"
import { SystemStatus } from "./components/SystemStatus"

type AppState =
  | { kind: "loading" }
  | { kind: "connected"; data: ApiHealthResponse }
  | { kind: "degraded"; data: ApiHealthResponse }
  | { kind: "unreachable" }

function App() {
  const [state, setState] = useState<AppState>({ kind: "loading" })

  useEffect(() => {
    let cancelled = false

    async function loadStatus() {
      try {
        const payload = await fetchHealth()
        if (cancelled) {
          return
        }

        setState({
          kind: payload.status === "ok" ? "connected" : "degraded",
          data: payload,
        })
      } catch {
        if (!cancelled) {
          setState({ kind: "unreachable" })
        }
      }
    }

    void loadStatus()

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="page-shell">
      <section className="hero-card">
        <p className="eyebrow">Milestone 1 foundation</p>
        <h1>HerbWire V2</h1>
        <p className="lede">
          This walking skeleton proves the first real connection in the platform:
          React frontend to FastAPI backend to PostgreSQL 17.
        </p>
      </section>

      <SystemStatus apiBaseUrl={getApiBaseUrl()} state={state} />
    </main>
  )
}

export default App
