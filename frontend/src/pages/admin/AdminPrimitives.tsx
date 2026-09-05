import { Activity, ChevronRight } from "lucide-react"
import type { ReactNode } from "react"

const statusTone = (status: string) => {
  const normalized = status.toLowerCase()
  return normalized === "healthy" || normalized === "completed" || normalized === "ready to publish" || normalized === "published" || normalized === "approved" || normalized === "succeeded"
    ? "bg-sage/30 text-forest"
    : normalized === "running" || normalized === "processing" || normalized === "active" || normalized.includes("review") || normalized.includes("held")
      ? "bg-gold/20 text-deep"
      : "bg-rust/15 text-rust"
}

export function AdminStatusPill({ children }: { children: string }) {
  return <span className={`inline-flex max-w-full items-center gap-1.5 rounded-full px-2.5 py-1 font-sans text-[10px] font-bold uppercase tracking-[.08em] ${statusTone(children)}`}><span className="h-1.5 w-1.5 shrink-0 rounded-full bg-current" />{children}</span>
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-col justify-between gap-5 border-b border-line pb-7 sm:flex-row sm:items-end">
      <div className="min-w-0"><p className="hw-eyebrow">{eyebrow}</p><h1 className="mt-2 font-serif text-[clamp(2.25rem,9vw,3rem)] font-semibold leading-tight tracking-[-.045em] text-deep">{title}</h1>{description ? <p className="mt-3 max-w-2xl font-serif text-base leading-relaxed text-muted sm:text-lg">{description}</p> : null}</div>
      {action ? <div className="max-w-full self-start sm:shrink-0 sm:self-auto">{action}</div> : null}
    </div>
  )
}

export function Metric({ label, value, detail, icon: Icon = Activity }: { label: string; value: string; detail: string; icon?: typeof Activity }) {
  return <div className="border border-line bg-paper p-5"><div className="flex items-center justify-between"><span className="hw-eyebrow">{label}</span><Icon size={17} className="text-leaf" /></div><p className="mt-5 font-serif text-4xl font-semibold tracking-[-.05em] text-deep">{value}</p><p className="mt-1 font-sans text-xs text-muted">{detail}</p></div>
}

export function Panel({ title, eyebrow, children, className = "" }: { title: string; eyebrow: string; children: ReactNode; className?: string }) {
  return <div className={`min-w-0 border border-line bg-paper p-4 sm:p-5 ${className}`}><div className="mb-3 flex items-end justify-between gap-3"><div className="min-w-0"><p className="hw-eyebrow">{eyebrow}</p><h2 className="mt-1 font-serif text-2xl font-semibold leading-tight text-deep">{title}</h2></div><ChevronRight size={16} className="shrink-0 text-leaf" /></div>{children}</div>
}

export function AdminStateCard({ eyebrow = "Editorial desk", title, description, action }: { eyebrow?: string; title: string; description: string; action?: ReactNode }) {
  return <div className="border border-line bg-sage/15 p-6 sm:p-8"><p className="hw-eyebrow">{eyebrow}</p><h2 className="mt-2 font-serif text-3xl font-semibold tracking-[-.045em] text-deep">{title}</h2><p className="mt-3 max-w-2xl font-sans text-sm leading-relaxed text-muted">{description}</p>{action ? <div className="mt-5">{action}</div> : null}</div>
}
