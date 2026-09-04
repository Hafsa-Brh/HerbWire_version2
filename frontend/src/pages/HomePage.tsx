import { ArrowUpRight, Check } from "lucide-react"
import { useCallback, useState } from "react"
import { Link } from "react-router-dom"
import { fetchPublishedDiscoveries, type ApiPublicDiscoveryArticle } from "../api/discoveries"
import { subscribeNewsletter } from "../api/newsletter"
import { ApiRequestError, fetchPlants } from "../api/plants"
import { HomeDiscoveryCarousel } from "../components/home/HomeDiscoveryCarousel"
import { PlantCard } from "../components/plants/PlantPrimitives"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

const SUBSCRIBE_DECOR =
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/image-9ABW0EekEPGKkE7l42ImkKQOCQPQa0.png"

export function HomePage() {
  const plants = useAsyncResource(useCallback((signal: AbortSignal) => fetchPlants(undefined, signal), []))
  const discoveries = useAsyncResource(useCallback((signal: AbortSignal) => fetchPublishedDiscoveries({}, signal), []))
  const plantList = plants.data ?? []
  const discoveryList = discoveries.data?.items ?? []
  const isLoading = plants.isLoading || discoveries.isLoading
  const hasError = plants.error || discoveries.error

  return (
    <SiteShell>
      <main id="top">
        {isLoading ? <RouteState eyebrow="HerbWire / loading" title="Loading the front page." description="Gathering the latest reviewed discoveries and plant profiles." primaryAction={{ label: "Return home", to: "/" }} /> : null}
        {hasError ? <RouteState eyebrow="HerbWire / interrupted" title="The wire paused unexpectedly." description="We could not load the reviewed archive right now. Try the front page again in a moment." primaryAction={{ label: "Try again", onClick: () => { plants.reload(); discoveries.reload() } }} secondaryAction={{ label: "Browse plants", to: "/plants" }} /> : null}
        {!isLoading && !hasError && discoveryList.length ? <HomeDiscoveryCarousel items={discoveryList.slice(0, 4)} /> : null}
        {!isLoading && !hasError && !discoveryList.length ? <RouteState eyebrow="HerbWire / discoveries" title="No published discoveries yet." description="Only explicitly published editorial work can appear on the homepage." primaryAction={{ label: "Browse plants", to: "/plants" }} /> : null}
        {!isLoading && !hasError ? <LatestDiscoveries items={discoveryList.slice(4, 7)} /> : null}
        {!isLoading && !hasError ? <ReviewedPlants plants={plantList.slice(0, 3)} /> : null}
        <NewsletterSection />
      </main>
      <Footer />
    </SiteShell>
  )
}

function articleDate(article: ApiPublicDiscoveryArticle) {
  return new Date(article.sources[0]?.publication_date ?? article.published_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function LatestDiscoveries({ items }: { items: ApiPublicDiscoveryArticle[] }) {
  if (!items.length) return null
  return (
    <section className="hw-container border-b border-line py-14 md:py-20">
      <div className="flex flex-col gap-4 border-b-2 border-forest pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="hw-eyebrow">Latest discoveries</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">New evidence, carefully read</h2></div>
        <Link to="/discoveries" className="inline-flex min-h-11 items-center gap-2 self-start font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link sm:self-auto">More discoveries <ArrowUpRight size={14} /></Link>
      </div>
      <div className="grid gap-7 pt-8 md:grid-cols-3">
        {items.map((article) => (
          <Link key={article.id} to={`/discoveries/${article.slug}`} className="group block border-b border-line pb-7">
            <div className="aspect-[4/3] overflow-hidden rounded-xl bg-sage/20">{article.hero_image?.local_path ? <img src={article.hero_image.local_path} alt={article.hero_image.alt_text || "Discovery editorial cover"} className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]" /> : null}</div>
            <p className="mt-4 hw-eyebrow">{article.article_type ?? article.category}</p>
            <h3 className="mt-2 font-serif text-2xl font-semibold leading-tight text-deep transition group-hover:text-leaf">{article.headline}</h3>
            <p className="mt-3 font-sans text-[11px] uppercase tracking-[.1em] text-muted">{articleDate(article)}</p>
          </Link>
        ))}
      </div>
    </section>
  )
}

function ReviewedPlants({ plants }: { plants: Awaited<ReturnType<typeof fetchPlants>> }) {
  if (!plants.length) return null
  return (
    <section className="hw-container border-b border-line py-14 md:py-20">
      <div className="flex flex-col gap-4 border-b-2 border-forest pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="hw-eyebrow">From the encyclopedia</p><h2 className="mt-2 font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">Reviewed medicinal plants</h2></div>
        <div className="flex flex-col items-start gap-2 sm:items-end"><Link to="/plants" className="inline-flex min-h-11 items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link">More medicinal plants <ArrowUpRight size={14} /></Link></div>
      </div>
      <div className="grid gap-7 pt-8 sm:grid-cols-2 lg:grid-cols-3">{plants.map((plant) => <PlantCard key={plant.id} plant={plant} />)}</div>
    </section>
  )
}

function NewsletterSection() {
  const [email, setEmail] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "duplicate" | "invalid" | "error">("idle")

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email.trim()) { setStatus("invalid"); return }
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
          <div className="absolute bottom-[-8px] left-[8%] hidden h-56 w-44 -rotate-12 opacity-80 mix-blend-multiply md:block"><img src={SUBSCRIBE_DECOR} alt="" aria-hidden="true" className="h-full w-full object-contain" /></div>
          <div className="absolute bottom-[-12px] right-[9%] hidden h-52 w-40 rotate-[15deg] opacity-70 mix-blend-multiply md:block"><img src={SUBSCRIBE_DECOR} alt="" aria-hidden="true" className="h-full w-full object-contain" /></div>
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
        <div className="mt-7 flex items-center justify-center gap-2 font-sans text-[11px] uppercase tracking-[.13em] text-muted"><Check size={15} className="text-leaf" />Reviewed with attention, published with humility.</div>
      </div>
    </section>
  )
}
