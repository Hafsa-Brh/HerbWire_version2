import { useState, type FormEvent } from "react"
import { triggerPubMedRun } from "../../api/discoveries"
import { Panel } from "./AdminPrimitives"

function isoDate(daysAgo: number): string {
  const value = new Date()
  value.setUTCDate(value.getUTCDate() - daysAgo)
  return value.toISOString().slice(0, 10)
}

export function PubMedRunControl({ onCreated }: { onCreated: () => void }) {
  const [startDate, setStartDate] = useState(isoDate(7))
  const [endDate, setEndDate] = useState(isoDate(0))
  const [maxRecords, setMaxRecords] = useState(5)
  const [dateType, setDateType] = useState<"publication" | "indexing">("publication")
  const [status, setStatus] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setStatus("")
    try {
      await triggerPubMedRun({
        start_date: startDate,
        end_date: endDate,
        max_records: maxRecords,
        date_type: dateType,
      })
      setStatus("Bounded PubMed run recorded. Review its stages and private drafts.")
      onCreated()
    } catch {
      setStatus("The run was rejected or failed safely. Review the persisted stage result.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel eyebrow="Manual authenticated trigger" title="Collect from PubMed">
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-5">
        <label className="grid gap-2 font-sans text-xs font-bold text-forest">
          Start date
          <input aria-label="PubMed start date" type="date" required value={startDate} onChange={(event) => setStartDate(event.target.value)} className="min-h-11 border border-line bg-paper px-3 font-normal" />
        </label>
        <label className="grid gap-2 font-sans text-xs font-bold text-forest">
          End date
          <input aria-label="PubMed end date" type="date" required value={endDate} onChange={(event) => setEndDate(event.target.value)} className="min-h-11 border border-line bg-paper px-3 font-normal" />
        </label>
        <label className="grid gap-2 font-sans text-xs font-bold text-forest">
          Date field
          <select aria-label="PubMed date field" value={dateType} onChange={(event) => setDateType(event.target.value as "publication" | "indexing")} className="min-h-11 border border-line bg-paper px-3 font-normal">
            <option value="publication">Publication</option>
            <option value="indexing">Indexing</option>
          </select>
        </label>
        <label className="grid gap-2 font-sans text-xs font-bold text-forest">
          Maximum records
          <input aria-label="Maximum PubMed records" type="number" min={1} max={5} required value={maxRecords} onChange={(event) => setMaxRecords(Number(event.target.value))} className="min-h-11 border border-line bg-paper px-3 font-normal" />
        </label>
        <button type="submit" disabled={busy} className="self-end bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream disabled:opacity-40">
          {busy ? "Running…" : "Run once"}
        </button>
      </form>
      <p className="mt-3 font-sans text-xs leading-relaxed text-muted">
        Official NCBI E-utilities only. The server enforces five records and a 31-day maximum window. Valid drafts remain private and require human review.
      </p>
      {status ? <p role="status" className="mt-3 bg-sage/20 p-3 font-sans text-sm text-deep">{status}</p> : null}
    </Panel>
  )
}