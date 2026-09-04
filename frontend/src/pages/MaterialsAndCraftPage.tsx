import { MapPin } from "lucide-react"
import { useCallback, useEffect } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { fetchMaterials, type MaterialSummary } from "../api/materials"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

function StoryCard({ story }: { story: MaterialSummary }) {
  return (
    <Link
      to={`/materials-and-craft/${story.slug}`}
      className="group block border-b border-line pb-7"
    >
      <div className="aspect-[4/3] overflow-hidden bg-sage/20">
        <img
          src={story.hero_media.local_path}
          alt={story.hero_media.alt_text}
          className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025] motion-reduce:transition-none motion-reduce:group-hover:scale-100"
        />
      </div>

      <p className="mt-4 hw-eyebrow">
        {story.category} / {story.material_labels[0]}
      </p>

      <h2 className="mt-2 font-serif text-2xl font-semibold leading-tight text-deep transition group-hover:text-leaf">
        {story.title}
      </h2>

      <p className="mt-3 line-clamp-3 font-serif text-base leading-relaxed text-muted">
        {story.deck}
      </p>

      <div className="mt-4 flex items-center justify-between gap-3 font-sans text-[11px] uppercase tracking-[.08em] text-muted">
        <span>{story.reading_time_minutes} min read</span>

        {story.geography_label ? (
          <span className="inline-flex items-center gap-1">
            <MapPin size={12} />
            {story.geography_label}
          </span>
        ) : null}
      </div>
    </Link>
  )
}

export function MaterialsAndCraftPage() {
  const [params, setParams] = useSearchParams()
  const requestedCategory = params.get("category") ?? ""

  // Load the complete collection once. Filtering is performed locally so the
  // hero and surrounding page never disappear or change between categories.
  const data = useAsyncResource(
    useCallback((signal: AbortSignal) => fetchMaterials("", signal), []),
  )

  const categories = data.data?.categories ?? []
  const validCategory = categories.includes(requestedCategory)
    ? requestedCategory
    : ""

  useEffect(() => {
    if (
      data.data &&
      requestedCategory &&
      !data.data.categories.includes(requestedCategory)
    ) {
      setParams({}, { replace: true })
    }
  }, [data.data, requestedCategory, setParams])

  if (data.isLoading) {
    return (
      <SiteShell>
        <RouteState
          eyebrow="Material stories"
          title="Opening the collection."
          description="Loading the reviewed materials archive."
          primaryAction={{ label: "Return home", to: "/" }}
        />
      </SiteShell>
    )
  }

  if (data.error || !data.data) {
    return (
      <SiteShell>
        <RouteState
          eyebrow="Material stories"
          title="The collection is unavailable."
          description="The material stories could not be loaded."
          primaryAction={{ label: "Try again", onClick: data.reload }}
        />
      </SiteShell>
    )
  }

  const { items, total } = data.data
  const featured = items.find((item) => item.featured) ?? items[0]

  const visibleStories = validCategory
    ? items.filter((story) => story.category === validCategory)
    : items

  function selectCategory(category: string) {
    if (category) {
      setParams({ category })
    } else {
      setParams({})
    }
  }

  return (
    <SiteShell>
      <main>
        <section className="hw-container py-10 md:py-14">
          <div className="grid items-center gap-8 border-b border-line pb-10 md:grid-cols-[minmax(0,.95fr)_minmax(0,1.05fr)] md:gap-10 lg:gap-14">
            <div className="min-w-0">
              <p className="hw-eyebrow">Material stories</p>

              <h1 className="mt-4 max-w-[13ch] font-serif text-[clamp(2.6rem,5vw,5.2rem)] font-semibold leading-[.94] tracking-[-.055em] text-deep">
                Made by hand, shaped by the living world.
              </h1>

              <p className="mt-6 max-w-xl font-serif text-lg leading-relaxed text-muted md:text-xl">
                Materials carry botanical, cultural and practical knowledge.
                This collection follows fibres, vessels, pigments and wood
                through carefully sourced acts of making.
              </p>
            </div>

            {featured ? (
              <Link
                to={`/materials-and-craft/${featured.slug}`}
                className="group block min-w-0"
                aria-label={`Read material story: ${featured.title}`}
              >
                <div className="aspect-video overflow-hidden rounded-tr-[3rem] bg-sage/20 md:rounded-tr-[4rem]">
                  <img
                    src={featured.hero_media.local_path}
                    alt={featured.hero_media.alt_text}
                    className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.02] motion-reduce:transition-none motion-reduce:group-hover:scale-100"
                  />
                </div>
              </Link>
            ) : null}
          </div>
        </section>

        <section className="hw-container pb-14 md:pb-20">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b-2 border-forest pb-4">
            <div>
              <p className="hw-eyebrow">{total} researched stories</p>
              <h2 className="mt-2 font-serif text-4xl font-semibold text-deep md:text-5xl">
                Explore the collection
              </h2>
            </div>
          </div>

          <nav
            aria-label="Material categories"
            className="flex flex-wrap gap-2 py-6"
          >
            <button
              type="button"
              onClick={() => selectCategory("")}
              aria-pressed={!validCategory}
              className={`min-h-11 border px-4 font-sans text-xs font-bold uppercase tracking-[.08em] transition ${
                !validCategory
                  ? "border-forest bg-forest text-cream"
                  : "border-line text-forest hover:border-leaf"
              }`}
            >
              All
            </button>

            {categories.map((category) => (
              <button
                type="button"
                key={category}
                onClick={() => selectCategory(category)}
                aria-pressed={validCategory === category}
                className={`min-h-11 border px-4 font-sans text-xs font-bold uppercase tracking-[.08em] transition ${
                  validCategory === category
                    ? "border-forest bg-forest text-cream"
                    : "border-line text-forest hover:border-leaf"
                }`}
              >
                {category}
              </button>
            ))}
          </nav>

          {visibleStories.length ? (
            <div
              data-testid="material-results"
              className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3"
            >
              {visibleStories.map((story) => (
                <StoryCard key={story.id} story={story} />
              ))}
            </div>
          ) : (
            <div className="border-y border-line py-16 text-center">
              <h2 className="font-serif text-3xl text-deep">
                No stories in this category
              </h2>

              <button
                type="button"
                onClick={() => selectCategory("")}
                className="mt-5 font-sans text-xs font-bold uppercase text-leaf"
              >
                View all materials
              </button>
            </div>
          )}

          <aside className="mt-14 border-t border-line pt-6 font-sans text-sm text-muted">
            <strong className="text-deep">Material index:</strong> {total}{" "}
            curated stories across {categories.length} documented categories.
            Every story includes institutional provenance and licensed media.
          </aside>
        </section>
      </main>

      <Footer />
    </SiteShell>
  )
}