import { Link } from "react-router-dom"

type RouteStateAction = { label: string; to?: string; onClick?: () => void }

type RouteStateProps = {
  eyebrow: string
  title: string
  description: string
  primaryAction: RouteStateAction
  secondaryAction?: RouteStateAction
}

function RouteStateActionButton({ action, muted = false }: { action: RouteStateAction; muted?: boolean }) {
  const className = muted
    ? "inline-flex items-center gap-2 border border-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-forest transition hover:bg-forest hover:text-cream"
    : "inline-flex items-center gap-2 bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream transition hover:bg-leaf"
  if (action.to) return <Link to={action.to} className={className}>{action.label}</Link>
  return <button type="button" onClick={action.onClick} className={className}>{action.label}</button>
}

export function RouteState({ eyebrow, title, description, primaryAction, secondaryAction }: RouteStateProps) {
  return (
    <section className="hw-container py-14 md:py-20">
      <div className="border-y border-line bg-sage/15 p-6 sm:p-8">
        <p className="hw-eyebrow">{eyebrow}</p>
        <h1 className="mt-3 max-w-3xl font-serif text-[clamp(2.45rem,5.2vw,5rem)] font-semibold leading-[.93] tracking-[-.06em] text-deep">{title}</h1>
        <p className="mt-5 max-w-2xl font-serif text-lg leading-relaxed text-muted md:text-xl">{description}</p>
        <div className="mt-7 flex flex-wrap gap-3">
          <RouteStateActionButton action={primaryAction} />
          {secondaryAction ? <RouteStateActionButton action={secondaryAction} muted /> : null}
        </div>
      </div>
    </section>
  )
}
