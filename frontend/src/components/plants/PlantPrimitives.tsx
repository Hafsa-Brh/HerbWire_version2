import { ArrowUpRight } from "lucide-react"
import { Link } from "react-router-dom"
import loginMonsteraImage from "../../assets/login-monstera.png"
import type { ApiPlantListItem } from "../../api/plants"

export function StatusPill({ children }: { children: string }) {
  const normalized = children.toLowerCase()
  const tone = normalized === "published" || normalized === "approved" ? "bg-sage/30 text-forest" : normalized.includes("review") || normalized.includes("held") ? "bg-gold/20 text-deep" : "bg-rust/15 text-rust"
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-sans text-[10px] font-bold uppercase tracking-[.08em] ${tone}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{children}</span>
}

export function BotanicalImage({ label, compact = false }: { label: string; compact?: boolean }) {
  return (
    <div className={`relative overflow-hidden rounded-xl bg-sage/30 ${compact ? "aspect-[4/3]" : "aspect-[16/9]"}`} role="img" aria-label={`Botanical image treatment for ${label}`}>
      <img className="hw-image h-full w-full object-cover opacity-80" src={loginMonsteraImage} alt="" aria-hidden="true" loading="lazy" />
      <div className="absolute inset-0 bg-gradient-to-t from-deep/55 via-deep/5 to-transparent" />
    </div>
  )
}

export function PlantCard({ plant }: { plant: ApiPlantListItem }) {
  return (
    <article className="group">
      <Link to={`/plants/${plant.slug}`} className="block">
        <div className="hw-image-wrap relative aspect-[4/3] overflow-hidden rounded-xl bg-sage/30">
          <BotanicalImage label={plant.display_common_name} compact />
          <div className="absolute left-3 top-3 bg-paper px-2 py-1"><StatusPill>{plant.status}</StatusPill></div>
        </div>
        <div className="pt-5">
          <p className="hw-eyebrow">{plant.family_name ?? "Family under review"}</p>
          <h3 className="mt-2 font-serif text-[1.45rem] font-semibold leading-[1.08] tracking-[-.025em] text-deep transition group-hover:text-leaf sm:text-[1.6rem]">{plant.display_common_name}</h3>
          <p className="mt-2 font-serif text-sm italic text-muted">{plant.accepted_scientific_name}</p>
          <p className="mt-3 font-serif text-[15px] leading-relaxed text-muted">{plant.summary}</p>
          <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 font-sans text-[11px] text-muted">
            <span>{plant.source_count} provenance sources</span><span aria-hidden="true">/</span><span className="inline-flex items-center gap-1 font-sans text-xs font-bold text-leaf">Read profile <ArrowUpRight size={14} /></span>
          </div>
        </div>
      </Link>
    </article>
  )
}
