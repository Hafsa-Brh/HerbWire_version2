import { ArrowLeft, ArrowRight, ArrowUpRight, ImageOff } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import type { MaterialSummary } from "../../api/materials"

type HomeMaterialsCarouselProps = {
  items: MaterialSummary[]
  isLoading?: boolean
  error?: Error | null
  onRetry?: () => void
}

const AUTOPLAY_MS = 3000

function storyPath(story: MaterialSummary) {
  return `/materials-and-craft/${story.slug}`
}

export function HomeMaterialsCarousel({ items, isLoading = false, error = null, onRetry }: HomeMaterialsCarouselProps) {
  const [index, setIndex] = useState(0)
  const [timerKey, setTimerKey] = useState(0)
  const [hovered, setHovered] = useState(false)
  const [focused, setFocused] = useState(false)
  const [hidden, setHidden] = useState(document.visibilityState === "hidden")
  const [reducedMotion, setReducedMotion] = useState(false)
  const [failedImages, setFailedImages] = useState<Set<string>>(() => new Set())
  const touchStart = useRef<number | null>(null)
  const count = items.length

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return
    const media = window.matchMedia("(prefers-reduced-motion: reduce)")
    const update = () => setReducedMotion(media.matches)
    update()
    media.addEventListener("change", update)
    return () => media.removeEventListener("change", update)
  }, [])

  useEffect(() => {
    const update = () => setHidden(document.visibilityState === "hidden")
    document.addEventListener("visibilitychange", update)
    return () => document.removeEventListener("visibilitychange", update)
  }, [])

  useEffect(() => {
    if (count < 2 || hovered || focused || hidden || reducedMotion) return
    const timer = window.setTimeout(() => setIndex((value) => (value + 1) % count), AUTOPLAY_MS)
    return () => window.clearTimeout(timer)
  }, [count, focused, hidden, hovered, index, reducedMotion, timerKey])

  const normalizedIndex = count ? index % count : 0
  const active = count ? items[normalizedIndex] : null
  const previous = count > 1 ? items[(normalizedIndex - 1 + count) % count] : null
  const next = count > 1 ? items[(normalizedIndex + 1) % count] : null

  function move(step: number) {
    if (count) {
      setIndex((value) => (value + step + count) % count)
      setTimerKey((value) => value + 1)
    }
  }

  function markImageFailed(slug: string) {
    setFailedImages((values) => new Set(values).add(slug))
  }

  return (
    <section aria-labelledby="home-materials-heading" className="hw-container border-b border-line py-14 md:py-20">
      <div className="flex flex-col gap-4 border-t border-line pt-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="hw-eyebrow">From the field cabinet</p>
          <h2 id="home-materials-heading" className="mt-2 max-w-[18ch] font-serif text-4xl font-semibold tracking-[-.04em] text-deep md:text-5xl">
            Materials shaped by patient hands
          </h2>
        </div>
        <Link to="/materials-and-craft" className="inline-flex min-h-11 items-center gap-2 self-start font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link sm:self-auto">
          Explore Materials &amp; Craft <ArrowUpRight size={14} />
        </Link>
      </div>

      {isLoading ? (
        <p role="status" className="border-y border-line py-14 text-center font-serif text-lg text-muted">Opening the material stories.</p>
      ) : error ? (
        <div className="border-y border-line py-12 text-center">
          <p role="status" className="font-serif text-lg text-muted">The material stories are temporarily unavailable.</p>
          {onRetry ? <button type="button" onClick={onRetry} className="mt-4 min-h-11 font-sans text-xs font-bold uppercase tracking-[.12em] text-leaf hw-link">Try again</button> : null}
        </div>
      ) : !active ? (
        <p role="status" className="border-y border-line py-14 text-center font-serif text-lg text-muted">No published material stories are available yet.</p>
      ) : (
        <div role="region" aria-roledescription="carousel" aria-label="Featured material stories" className="pt-8 md:pt-10"
          onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} onFocusCapture={() => setFocused(true)}
          onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false) }}
          onTouchStart={(event) => { touchStart.current = event.touches[0]?.clientX ?? null }}
          onTouchEnd={(event) => { if (touchStart.current === null) return; const delta = (event.changedTouches[0]?.clientX ?? touchStart.current) - touchStart.current; if (Math.abs(delta) > 45) move(delta > 0 ? -1 : 1); touchStart.current = null }}>
          <div className="grid items-center justify-items-center gap-5 md:grid-cols-[minmax(0,.62fr)_minmax(0,1.35fr)_minmax(0,.62fr)] md:gap-4 lg:gap-8">
            {previous ? (
              <Link key={previous.slug} to={storyPath(previous)} aria-label={`Read previous material story: ${previous.title}`} className="hw-material-slide-enter group hidden w-full max-w-[10.5rem] md:block">
                <div className="aspect-square overflow-hidden rounded-[48%] border border-leaf/50 bg-sage/20 p-1">
                  {failedImages.has(previous.slug) ? <ImageFallback /> : <img src={previous.hero_media.local_path} alt={previous.hero_media.alt_text} onError={() => markImageFailed(previous.slug)} className="h-full w-full rounded-[48%] object-cover transition duration-500 group-hover:scale-[1.025] motion-reduce:transition-none motion-reduce:group-hover:scale-100" />}
                </div>
                <p className="mt-4 line-clamp-2 text-center font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest">{previous.category}</p>
              </Link>
            ) : <span aria-hidden="true" />}

            <Link key={active.slug} to={storyPath(active)} aria-label={`Read material story: ${active.title}`} className="hw-material-slide-enter group block w-full max-w-[29rem]">
              <div className="aspect-[4/3] overflow-hidden rounded-[44%] border border-leaf/50 bg-sage/20 p-1 sm:aspect-[5/4]">
                {failedImages.has(active.slug) ? <ImageFallback /> : <img src={active.hero_media.local_path} alt={active.hero_media.alt_text} onError={() => markImageFailed(active.slug)} className="h-full w-full rounded-[44%] object-cover transition duration-500 group-hover:scale-[1.02] motion-reduce:transition-none motion-reduce:group-hover:scale-100" />}
              </div>
            </Link>

            {next ? (
              <Link key={next.slug} to={storyPath(next)} aria-label={`Read next material story: ${next.title}`} className="hw-material-slide-enter group hidden w-full max-w-[10.5rem] md:block">
                <div className="aspect-square overflow-hidden rounded-[48%] border border-leaf/50 bg-sage/20 p-1">
                  {failedImages.has(next.slug) ? <ImageFallback /> : <img src={next.hero_media.local_path} alt={next.hero_media.alt_text} onError={() => markImageFailed(next.slug)} className="h-full w-full rounded-[48%] object-cover transition duration-500 group-hover:scale-[1.025] motion-reduce:transition-none motion-reduce:group-hover:scale-100" />}
                </div>
                <p className="mt-4 line-clamp-2 text-center font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest">{next.category}</p>
              </Link>
            ) : <span aria-hidden="true" />}
          </div>

          <div key={`copy-${active.slug}`} className="hw-material-copy-enter mx-auto mt-7 max-w-2xl text-center">
            <p className="hw-eyebrow">{active.geography_label ? `${active.geography_label} / ` : ""}{active.category}</p>
            <h3 className="mt-2 font-serif text-3xl font-semibold leading-tight tracking-[-.03em] text-deep md:text-4xl">
              <Link to={storyPath(active)} className="transition hover:text-leaf">{active.title}</Link>
            </h3>
            <p className="mx-auto mt-3 line-clamp-2 max-w-xl font-serif text-base leading-relaxed text-muted md:text-lg">{active.deck}</p>
            <Link to={storyPath(active)} className="mt-3 inline-flex min-h-11 items-center gap-2 font-serif text-base text-leaf hw-link">Discover the craft <ArrowUpRight size={14} /></Link>

            <div className="mx-auto mt-3 flex max-w-md items-center gap-4">
              <button type="button" onClick={() => move(-1)} aria-label="Show previous material story" className="grid h-12 w-12 shrink-0 place-items-center rounded-full border border-leaf text-forest transition hover:bg-sage/20"><ArrowLeft size={19} /></button>
              <div className="min-w-0 flex-1">
                <span className="font-sans text-xs font-bold text-forest">{String(normalizedIndex + 1).padStart(2, "0")} / {String(count).padStart(2, "0")}</span>
                <div className="mt-3 h-px bg-line" role="progressbar" aria-label="Material stories progress" aria-valuemin={1} aria-valuemax={count} aria-valuenow={normalizedIndex + 1}><div aria-hidden="true" className="h-px bg-leaf transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${((normalizedIndex + 1) / count) * 100}%` }} /></div>
              </div>
              <button type="button" onClick={() => move(1)} aria-label="Show next material story" className="grid h-12 w-12 shrink-0 place-items-center rounded-full border border-leaf text-forest transition hover:bg-sage/20"><ArrowRight size={19} /></button>
            </div>
          </div>
          <p className="sr-only" aria-live="polite" aria-atomic="true">Material story {normalizedIndex + 1} of {count}: {active.title}</p>
        </div>
      )}
    </section>
  )
}

function ImageFallback() {
  return <div className="grid h-full place-items-center rounded-[44%] text-center text-muted"><div><ImageOff className="mx-auto" size={28} /><span className="sr-only">Image temporarily unavailable</span></div></div>
}
