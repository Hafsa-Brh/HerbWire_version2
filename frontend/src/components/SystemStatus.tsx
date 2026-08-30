import type { ApiHealthResponse } from "../api/health"

type SystemStatusState =
  | { kind: "loading" }
  | { kind: "connected"; data: ApiHealthResponse }
  | { kind: "degraded"; data: ApiHealthResponse }
  | { kind: "unreachable" }

type SystemStatusProps = {
  apiBaseUrl: string
  state: SystemStatusState
}

export function SystemStatus({ apiBaseUrl, state }: SystemStatusProps) {
  return (
    <section aria-labelledby="system-status-heading" className="status-card">
      <div className="status-card__header">
        <div>
          <h2 id="system-status-heading">System status</h2>
          <p className="status-card__subtle">Real backend and database connectivity only.</p>
        </div>
        <code>{apiBaseUrl}</code>
      </div>

      <div aria-live="polite" role="status" className="status-banner">
        {state.kind === "loading" && <p>Checking backend and database connectivity...</p>}
        {state.kind === "connected" && <p>Backend reachable. Database connection is healthy.</p>}
        {state.kind === "degraded" && <p>Backend reachable, but the database connection is unavailable.</p>}
        {state.kind === "unreachable" && <p>Backend is unavailable from the frontend.</p>}
      </div>

      {state.kind !== "unreachable" && state.kind !== "loading" && (
        <dl className="status-grid">
          <div>
            <dt>Service</dt>
            <dd>{state.data.service}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>{state.data.version}</dd>
          </div>
          <div>
            <dt>Overall status</dt>
            <dd>{state.data.status}</dd>
          </div>
          <div>
            <dt>Database</dt>
            <dd>{state.data.database}</dd>
          </div>
        </dl>
      )}
    </section>
  )
}
