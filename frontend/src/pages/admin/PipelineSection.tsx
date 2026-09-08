import { RotateCcw } from "lucide-react"
import { Link } from "react-router-dom"
import type {
  GenerationItem,
  GenerationRun,
  PipelineAvailability,
} from "../../api/pipelines"
import { AdminStatusPill, Panel } from "./AdminPrimitives"

type PipelineSectionProps = {
  domain: "plants" | "discoveries"
  count: number
  allAvailable: boolean
  availability: PipelineAvailability | null
  run: GenerationRun | null
  busy: boolean
  blockedBy: string | null
  error: string
  onCount: (count: number) => void
  onAllAvailable: (selected: boolean) => void
  onStart: () => void
  onRetry: () => void
}

function editorialStatus(item: GenerationItem) {
  if (item.status === "held") return "Held"
  if (item.status === "failed") return "Failed"
  const status = item.editorial_status ?? item.status
  if (status === "needs_review") return "Private review"
  if (status === "held") return "Held"
  if (status === "failed" || status === "rejected") return "Failed"
  if (status === "approved") return "Approved — private"
  if (status === "published") return "Published"
  return "Private review"
}

export function PipelineResultPanel({
  domain,
  run,
}: {
  domain: PipelineSectionProps["domain"]
  run: GenerationRun | null
}) {
  const generated = run?.items.filter((item) => item.title) ?? []
  const label = domain === "plants" ? "Plants pipeline results" : "Discoveries pipeline results"

  return (
    <section
      aria-label={label}
      className="min-h-56 min-w-0 border border-line bg-paper p-5 sm:p-6"
    >
      {run?.status === "running" ? (
        <p
          role="status"
          aria-live="polite"
          className="font-sans text-xs font-bold uppercase tracking-[.1em] text-leaf"
        >
          Running
        </p>
      ) : null}
      {generated.length ? (
        <ul className={run?.status === "running" ? "mt-4 grid gap-3" : "grid gap-3"}>
          {generated.map((item) => {
            const destination = item.review_id
              ? domain === "plants"
                ? `/admin/reviews?review=${item.review_id}`
                : `/admin/discoveries?article=${item.discovery_article_id}`
              : null
            return (
              <li
                key={item.id}
                className="flex min-w-0 flex-col gap-2 border-b border-line pb-3 last:border-b-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
              >
                {destination ? (
                  <Link
                    to={destination}
                    className="min-w-0 break-words font-serif text-lg font-semibold text-deep underline decoration-line underline-offset-4 hover:text-leaf"
                  >
                    {item.title}
                  </Link>
                ) : (
                  <strong className="min-w-0 break-words font-serif text-lg text-deep">
                    {item.title}
                  </strong>
                )}
                <AdminStatusPill>{editorialStatus(item)}</AdminStatusPill>
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}

export function PipelineSection(props: PipelineSectionProps) {
  const {
    domain,
    count,
    allAvailable,
    availability,
    run,
    busy,
    blockedBy,
    error,
  } = props
  const isPlants = domain === "plants"
  const active = run?.status === "running"
  const canRetry = run?.status === "failed"
  const controlsDisabled = active || busy || Boolean(blockedBy)
  const launchDisabled =
    controlsDisabled || availability === null || !availability.can_start

  return (
    <section aria-labelledby={`${domain}-pipeline-title`} className="min-w-0">
      <div className="grid min-w-0 gap-5 lg:grid-cols-2">
        <Panel
          eyebrow="Source-led generation"
          title={isPlants ? "Plants pipeline" : "Discoveries pipeline"}
        >
          <span id={`${domain}-pipeline-title`} className="sr-only">
            {isPlants ? "Plants pipeline" : "Discoveries pipeline"}
          </span>
          <label
            htmlFor={`${domain}-count`}
            className="block font-sans text-sm font-semibold text-deep"
          >
            {isPlants ? "Profiles to generate" : "Articles to generate"}
          </label>
          <input
            id={`${domain}-count`}
            type="number"
            min={1}
            max={10}
            step={1}
            value={count}
            disabled={controlsDisabled || allAvailable}
            onChange={(event) =>
              props.onCount(
                Math.min(10, Math.max(1, Number(event.target.value) || 1)),
              )
            }
            className="mt-2 min-h-11 w-28 max-w-full border border-line bg-paper px-3 font-sans text-base text-deep disabled:opacity-50"
          />
          <label className="mt-3 flex min-h-11 items-center gap-3 font-sans text-sm font-semibold text-deep">
            <input
              type="checkbox"
              aria-label={isPlants ? "All available Plant profiles" : "All available Discovery articles"}
              checked={allAvailable}
              disabled={controlsDisabled}
              onChange={(event) => props.onAllAvailable(event.target.checked)}
              className="h-5 w-5 accent-leaf"
            />
            All available
          </label>
          <p className="mt-3 max-w-xl font-sans text-sm leading-relaxed text-muted">
            Each {isPlants ? "profile" : "article"} completes before the next
            begins. Successful drafts remain private until separate review and
            publication.
          </p>
          {blockedBy ? (
            <p role="status" className="mt-3 font-sans text-sm text-rust">
              The {blockedBy} pipeline is currently active.
            </p>
          ) : null}
          <button
            type="button"
            disabled={launchDisabled}
            onClick={props.onStart}
            className="mt-5 min-h-11 w-full bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.08em] text-cream hover:bg-leaf disabled:cursor-not-allowed disabled:opacity-45 sm:w-auto"
          >
            {active || busy
              ? `Running the ${isPlants ? "Plants" : "Discoveries"} pipeline…`
              : `Run the ${isPlants ? "Plants" : "Discoveries"} pipeline`}
          </button>
          {canRetry ? (
            <button
              type="button"
              onClick={props.onRetry}
              disabled={busy || Boolean(blockedBy)}
              className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 border border-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.08em] text-forest disabled:opacity-45 sm:ml-3 sm:w-auto"
            >
              <RotateCcw size={15} /> Resume / Retry
            </button>
          ) : null}
          {error || (!availability?.can_start && availability?.unavailable_reason) ? (
            <p role="alert" className="mt-3 font-sans text-sm text-rust">
              {error || availability?.unavailable_reason}
            </p>
          ) : null}
        </Panel>
        <PipelineResultPanel domain={domain} run={run} />
      </div>
    </section>
  )
}
