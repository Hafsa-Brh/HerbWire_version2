import { useCallback, useEffect, useState } from "react"
import {
  discoveriesPipelineApi,
  plantsPipelineApi,
  type GenerationRun,
  type PipelineApi,
  type PipelineAvailability,
} from "../../api/pipelines"
import { PageHeader } from "./AdminPrimitives"
import { PipelineSection } from "./PipelineSection"

function storedRunKey(domain: "plants" | "discoveries") {
  return `herbwire.pipeline.${domain}.run`
}

function usePipeline(domain: "plants" | "discoveries", api: PipelineApi) {
  const [count, setCount] = useState(1)
  const [allAvailable, setAllAvailable] = useState(false)
  const [availability, setAvailability] = useState<PipelineAvailability | null>(null)
  const [run, setRun] = useState<GenerationRun | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  const refreshAvailability = useCallback(
    async (signal?: AbortSignal) => {
      setAvailability(await api.availability(count, allAvailable, signal))
    },
    [allAvailable, api, count],
  )

  useEffect(() => {
    const controller = new AbortController()
    const runId = window.sessionStorage.getItem(storedRunKey(domain))
    const load = async () => {
      const availabilityRequest = refreshAvailability(controller.signal)
      if (runId) {
        try {
          setRun(await api.read(runId, controller.signal))
        } catch {
          if (!controller.signal.aborted) {
            window.sessionStorage.removeItem(storedRunKey(domain))
            setRun(null)
          }
        }
      }
      await availabilityRequest
    }
    void load().catch(() => {
      if (!controller.signal.aborted) {
        setError("Pipeline status is temporarily unavailable.")
      }
    })
    return () => controller.abort()
  }, [api, domain, refreshAvailability])

  useEffect(() => {
    if (run?.status !== "running") return
    const timer = window.setInterval(() => {
      void api
        .read(run.id)
        .then(setRun)
        .catch(() =>
          setError("Progress remains persisted, but could not be refreshed."),
        )
    }, 1000)
    return () => window.clearInterval(timer)
  }, [api, run])

  async function start() {
    if (busy || run?.status === "running") return
    setBusy(true)
    setError("")
    try {
      const nextRun = await api.start(count, crypto.randomUUID(), allAvailable)
      window.sessionStorage.setItem(storedRunKey(domain), nextRun.id)
      setRun(nextRun)
      await refreshAvailability()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The run could not be started.")
    } finally {
      setBusy(false)
    }
  }

  async function retry() {
    if (!run || busy) return
    setBusy(true)
    setError("")
    try {
      const nextRun = await api.retry(run.id)
      window.sessionStorage.setItem(storedRunKey(domain), nextRun.id)
      setRun(nextRun)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The run could not be resumed.")
    } finally {
      setBusy(false)
    }
  }

  return {
    count,
    setCount,
    allAvailable,
    setAllAvailable,
    availability,
    run,
    busy,
    error,
    start,
    retry,
  }
}

export function PipelinesPage() {
  const plants = usePipeline("plants", plantsPipelineApi)
  const discoveries = usePipeline("discoveries", discoveriesPipelineApi)
  const activePipeline =
    plants.availability?.active_pipeline ??
    discoveries.availability?.active_pipeline ??
    null

  return (
    <>
      <PageHeader
        eyebrow="Editorial / source-led automation"
        title="Pipelines"
        description="Launch bounded Plant and Discovery pipelines that create private drafts for editorial review."
      />
      <div className="grid min-w-0 gap-8">
        <PipelineSection
          domain="plants"
          {...plants}
          blockedBy={
            activePipeline && activePipeline !== "plants" ? "Discoveries" : null
          }
          onCount={plants.setCount}
          onAllAvailable={plants.setAllAvailable}
          onStart={plants.start}
          onRetry={plants.retry}
        />
        <PipelineSection
          domain="discoveries"
          {...discoveries}
          blockedBy={
            activePipeline && activePipeline !== "discoveries" ? "Plants" : null
          }
          onCount={discoveries.setCount}
          onAllAvailable={discoveries.setAllAvailable}
          onStart={discoveries.start}
          onRetry={discoveries.retry}
        />
      </div>
    </>
  )
}
