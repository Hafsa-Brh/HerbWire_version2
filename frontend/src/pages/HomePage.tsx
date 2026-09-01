import { ArrowUpRight, Check, Globe2 } from "lucide-react"
import { useCallback, useState } from "react"
import { Link } from "react-router-dom"
import { subscribeNewsletter } from "../api/newsletter"
import { ApiRequestError, fetchPlants } from "../api/plants"
import globalCoverageImage from "../assets/global-coverage.png"

const SUBSCRIBE_DECOR =
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/image-9ABW0EekEPGKkE7l42ImkKQOCQPQa0.png"
import { PlantCard } from "../components/plants/PlantPrimitives"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

export function HomePage() {
  const plants = useAsyncResource(useCallback((signal: AbortSignal) => fetchPlants(undefined, signal), []))
  const plantList = plants.data ?? []
  const leadPlant = plantList[0] ?? null
  const latest = plantList.slice(1, 4)

  return (
    <SiteShell>
      <main id="top">
        {plants.isLoading ? <RouteState eyebrow="HerbWire / loading" title="Loading the front page." description="The encyclopedia is gathering published plant profiles now." primaryAction={{ label: "Return home", to: "/" }} /> : null}
        {plants.error ? <RouteState eyebrow="HerbWire / interrupted" title="The wire paused unexpectedly." description="We could not load the public encyclopedia right now. Try the front page again in a moment." primaryAction={{ label: "Try again", onClick: plants.reload }} secondaryAction={{ label: "Browse plants", to: "/plants" }} /> : null}
        {!plants.isLoading && !plants.error && leadPlant ? (
          <section className="hw-container grid gap-8 border-b border-line py-10 md:grid-cols-[minmax(0,1fr)_310px] md:gap-14 md:py-16">
            <article className="group">
              <Link to={`/plants/${leadPlant.slug}`} className="block">
                <div className="hw-image-wrap relative aspect-[16/8] overflow-hidden rounded-2xl bg-sage">
                  <img src={globalCoverageImage} alt="A HerbWire globe graphic showing international botanical coverage" className="hw-image h-full w-full object-cover" />
                </div>
                <div className="max-w-3xl pt-6">
                  <p className="hw-eyebrow">Medicinal Plant Encyclopedia</p>
                  <h1 className="mt-3 max-w-3xl font-serif text-[clamp(2.45rem,5.2vw,5rem)] font-semibold leading-[.93] tracking-[-.06em] text-deep transition group-hover:text-leaf">{leadPlant.display_common_name}</h1>
                  <p className="mt-5 max-w-2xl font-serif text-lg leading-relaxed text-muted md:text-xl">{leadPlant.summary}</p>
                  <div className="mt-5 flex flex-wrap items-center gap-4 font-sans text-[11px] text-muted">
                    <span>{leadPlant.accepted_scientific_name}</span><span aria-hidden="true">/</span><span>{leadPlant.source_count} sources</span><span className="inline-flex items-center gap-1 font-sans text-xs font-bold text-leaf">Read profile <ArrowUpRight size={14} /></span>
                  </div>
                </div>
              </Link>
            </article>
            <aside className="border-t-2 border-forest pt-4 md:border-t-0 md:border-l md:border-line md:pl-7">
              <div className="flex items-baseline justify-between"><p className="hw-eyebrow">Published profiles</p><span className="font-serif text-sm italic text-muted">Wire / {plantList.length}</span></div>
              <div className="mt-2 divide-y divide-line">
                {plantList.map((plant, index) => <Link to={`/plants/${plant.slug}`} key={plant.id} className="group block py-4 first:pt-4"><div className="flex gap-4"><span className="font-serif text-2xl text-sage">{String(index + 1).padStart(2, "0")}</span><div><h2 className="font-serif text-xl font-semibold leading-tight tracking-[-.02em] text-deep group-hover:text-leaf">{plant.display_common_name}</h2><p className="mt-3 flex flex-wrap items-center gap-2 font-sans text-[10px] text-muted">{plant.accepted_scientific_name}</p></div></div></Link>)}
              </div>
              <Link to="/plants" className="mt-4 inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link">All plants <ArrowUpRight size={14} /></Link>
            </aside>
          </section>
        ) : null}
        {!plants.isLoading && !plants.error && !leadPlant ? <RouteState eyebrow="HerbWire / encyclopedia" title="No published profiles yet." description="Drafts stay in the editorial desk until human approval and publication." primaryAction={{ label: "Open plants", to: "/plants" }} /> : null}
        <section id="latest" className="hw-container py-14 md:py-20">
          <div className="flex items-end justify-between border-b-2 border-forest pb-4">
            <div><p className="hw-eyebrow">From the encyclopedia</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">Reviewed medicinal plants</h2></div>
            <span className="hidden font-serif text-sm italic text-muted sm:block">Careful profiles, clear limits</span>
          </div>
          {leadPlant ? <div className="grid gap-6 pt-8 sm:grid-cols-2 md:grid-cols-3 md:gap-8">{[leadPlant, ...latest].map((plant) => <PlantCard key={plant.id} plant={plant} />)}</div> : null}
        </section>
        <section className="hw-container grid gap-8 border-b border-line py-14 md:grid-cols-[1fr_1.1fr] md:items-center md:gap-16 md:py-20">
          <div>
            <div className="flex items-center gap-3"><Globe2 size={22} className="text-leaf" /><p className="hw-eyebrow">Global coverage</p></div>
            <h2 className="mt-4 max-w-xl font-serif text-4xl font-semibold leading-[.98] tracking-[-.045em] text-deep md:text-5xl">Medicinal knowledge is a world story.</h2>
            <p className="mt-5 max-w-lg font-serif text-lg leading-relaxed text-muted">HerbWire follows medicinal plants and traditional medicine with source provenance, cautious language, and explicit human review before publication.</p>
            <Link to="/discoveries" className="mt-6 inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link">View new discoveries <ArrowUpRight size={14} /></Link>
          </div>
          <div className="relative min-h-[280px] overflow-hidden rounded-[1.75rem] bg-deep text-cream shadow-[0_26px_60px_rgba(13,45,33,.18)]">
            <img src={globalCoverageImage} alt="A glowing world globe marked with HerbWire coverage points" className="absolute inset-0 h-full w-full object-cover opacity-90" />
            <div className="absolute inset-0 bg-gradient-to-r from-deep via-deep/36 to-deep/8" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_22%,rgba(169,196,165,.12),transparent_28%),radial-gradient(circle_at_84%_76%,rgba(199,158,78,.08),transparent_20%)]" />
          </div>
        </section>
        <NewsletterSection />
      </main>
      <Footer />
    </SiteShell>
  )
}

function NewsletterSection() {
  const [email, setEmail] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "duplicate" | "invalid" | "error">("idle")

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email.trim()) {
      setStatus("invalid")
      return
    }
    setStatus("loading")
    try {
      const result = await subscribeNewsletter(email)
      setStatus(result.status === "already_subscribed" ? "duplicate" : "success")
    } catch (error) {
      setStatus(error instanceof ApiRequestError && error.status === 422 ? "invalid" : "error")
    }
  }

  const message = {
    idle: "",
    loading: "Subscribing...",
    success: "You are subscribed. HerbWire will not send email until an approved sender is connected.",
    duplicate: "That address is already subscribed.",
    invalid: "Enter a valid email address.",
    error: "Subscription is unavailable right now. Please try again.",
  }[status]

  return (
    <section id="methodology" className="relative overflow-hidden border-b border-line bg-paper py-14 text-forest md:py-20">
      <div className="hw-container">
        <div className="relative min-h-[360px] overflow-hidden border-y border-line px-6 py-10 md:min-h-[390px] md:px-12">
          <div className="absolute inset-x-0 bottom-[-115px] h-48 rounded-[50%_50%_0_0/28%_28%_0_0] bg-sage/25" />
          <div className="absolute bottom-[-8px] left-[8%] hidden h-56 w-44 -rotate-12 opacity-80 mix-blend-multiply md:block">
            <img src={SUBSCRIBE_DECOR} alt="" aria-hidden="true" className="h-full w-full object-contain" />
          </div>
          <div className="absolute bottom-[-12px] right-[9%] hidden h-52 w-40 rotate-[15deg] opacity-70 mix-blend-multiply md:block">
            <img src={SUBSCRIBE_DECOR} alt="" aria-hidden="true" className="h-full w-full object-contain" />
          </div>
          <div className="relative z-10 mx-auto max-w-xl text-center">
            <p className="hw-eyebrow text-leaf">Stay connected</p>
            <h2 className="mt-3 font-serif text-4xl font-semibold leading-none tracking-[-.045em] text-forest md:text-5xl">A little green in your inbox.</h2>
            <p className="mx-auto mt-5 max-w-md font-serif text-lg leading-relaxed text-muted">Join us for thoughtful stories, botanical rituals, and new dispatches from the living world.</p>
            <form className="mx-auto mt-7 flex max-w-md flex-col gap-3 sm:flex-row" onSubmit={submit} noValidate>
              <label className="sr-only" htmlFor="newsletter-email">Email address</label>
              <input id="newsletter-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Your email address" className="min-h-11 flex-1 border border-line bg-background px-4 font-sans text-sm text-forest placeholder:text-muted focus:border-leaf focus:outline-none" />
              <button type="submit" disabled={status === "loading"} className="min-h-11 bg-leaf px-5 font-sans text-xs font-bold uppercase tracking-[.1em] text-cream transition hover:bg-forest disabled:opacity-60">{status === "loading" ? "Subscribing" : "Subscribe"}</button>
            </form>
            {message ? <p role="status" className={`mx-auto mt-3 max-w-md font-sans text-xs ${status === "invalid" || status === "error" ? "text-rust" : "text-muted"}`}>{message}</p> : null}
          </div>
        </div>
        <div className="mt-7 flex items-center justify-center gap-2 font-sans text-[11px] uppercase tracking-[.13em] text-muted">
          <Check size={15} className="text-leaf" />
          Reviewed with attention, published with humility.
        </div>
      </div>
    </section>
  )
}
