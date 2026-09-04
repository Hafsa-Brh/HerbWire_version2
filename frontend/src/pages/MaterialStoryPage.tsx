import { ArrowLeft, ArrowUpRight } from "lucide-react"
import { useCallback } from "react"
import { Link, useParams } from "react-router-dom"
import { fetchMaterial } from "../api/materials"
import { RouteState } from "../components/site/RouteState"
import { Footer, SiteShell } from "../components/site/SiteShell"
import { useAsyncResource } from "../hooks/useAsyncResource"

export function MaterialStoryPage() {
  const { slug = "" } = useParams()

  const data = useAsyncResource(
    useCallback(
      (signal: AbortSignal) => fetchMaterial(slug, signal),
      [slug],
    ),
  )

  if (data.isLoading) {
    return (
      <SiteShell>
        <RouteState
          eyebrow="Materials & Craft"
          title="Opening the story."
          description="Loading the curated material record."
          primaryAction={{
            label: "Materials & Craft",
            to: "/materials-and-craft",
          }}
        />
      </SiteShell>
    )
  }

  if (data.error || !data.data) {
    return (
      <SiteShell>
        <RouteState
          eyebrow="Materials & Craft"
          title="Material story not found."
          description="This public story is unavailable."
          primaryAction={{
            label: "Return to Materials & Craft",
            to: "/materials-and-craft",
          }}
        />
      </SiteShell>
    )
  }

  const story = data.data

  return (
    <SiteShell>
      <main>
        <article>
          <div className="hw-container pt-10 md:pt-16">
  <Link
    to="/materials-and-craft"
    className="inline-flex items-center gap-2 font-sans text-xs font-bold uppercase tracking-[.1em] text-leaf"
  >
    <ArrowLeft size={14} />
    Materials & Craft
  </Link>
</div>

<header className="hw-container">
  <div className="mx-auto max-w-4xl py-12 text-center md:py-20">
    <p className="hw-eyebrow">
      {story.category} / {story.material_labels.join(" · ")}
    </p>

    <h1 className="mt-4 font-serif text-[clamp(3rem,6vw,5.5rem)] font-semibold leading-[.92] tracking-[-.055em] text-deep">
      {story.title}
    </h1>

    <p className="mx-auto mt-7 max-w-2xl font-serif text-xl leading-relaxed text-muted">
      {story.deck}
    </p>

    <p className="mt-5 font-sans text-xs uppercase tracking-[.1em] text-muted">
      {story.geography_label ?? "Documented material practice"} /{" "}
      {story.reading_time_minutes} min read
    </p>
  </div>
</header>

          <figure className="hw-container">
  <div className="mx-auto max-w-3xl">
    <div className="aspect-video overflow-hidden rounded-xl bg-sage/20">
      <img
        src={story.hero_media.local_path}
        alt={story.hero_media.alt_text}
        className="h-full w-full object-cover"
      />
    </div>

    <figcaption className="py-3 font-sans text-[10px] leading-relaxed text-muted">
      {story.hero_media.title}. {story.hero_media.attribution}.{" "}
      <a
        href={story.hero_media.source_page}
        target="_blank"
        rel="noreferrer"
        className="text-leaf underline"
      >
        {story.hero_media.license}
      </a>
    </figcaption>
  </div>
</figure>

          <div className="hw-container py-14 md:py-24">
           <div className="mx-auto grid max-w-2xl gap-12">
              {story.sections.map((section) => (
                <section key={section.key}>
                  <h2 className="font-serif text-3xl font-semibold tracking-[-.03em] text-deep">
                    {section.heading}
                  </h2>

                  <p className="mt-4 font-serif text-lg leading-[1.75] text-muted">
                    {section.text}
                  </p>
                </section>
              ))}
            </div>

            <section
              aria-labelledby="material-sources-heading"
              className="mx-auto mt-16 max-w-2xl border-t-2 border-forest pt-7"
            >
              <p className="hw-eyebrow">Documentation</p>

              <h2
                id="material-sources-heading"
                className="mt-2 font-serif text-3xl font-semibold tracking-[-.03em] text-deep"
              >
                Source provenance
              </h2>

              <p className="mt-3 max-w-2xl font-serif text-base leading-relaxed text-muted">
                Institutional and collection records supporting this material
                story.
              </p>

              <ol className="mt-7 grid gap-6 md:grid-cols-2">
                {story.sources.map((source, index) => (
                  <li
                    key={source.id}
                    className="border-t border-line pt-5"
                  >
                    <p className="font-sans text-[10px] font-bold uppercase tracking-[.12em] text-muted">
                      Source {String(index + 1).padStart(2, "0")}
                    </p>

                    <a
                      href={source.canonical_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-block font-serif text-xl font-semibold leading-snug text-leaf underline decoration-leaf/40 underline-offset-4 transition hover:text-forest"
                    >
                      {source.title}
                    </a>

                    <p className="mt-2 font-sans text-xs leading-relaxed text-muted">
                      {source.source_name} /{" "}
                      {source.source_type.replaceAll("_", " ")}
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          </div>

          {story.related.length ? (
            <section className="border-t border-line">
              <div className="hw-container py-12">
                <p className="hw-eyebrow">Continue exploring</p>

                <div className="mt-6 grid gap-6 md:grid-cols-3">
                  {story.related.map((item) => (
                    <Link
                      key={item.id}
                      to={`/materials-and-craft/${item.slug}`}
                      className="group"
                    >
                      <img
                        src={item.hero_media.local_path}
                        alt={item.hero_media.alt_text}
                        className="aspect-video w-full object-cover"
                      />

                      <h2 className="mt-3 font-serif text-xl font-semibold text-deep transition group-hover:text-leaf">
                        {item.title}
                      </h2>

                      <span className="mt-2 inline-flex items-center gap-1 font-sans text-xs text-leaf">
                        Read story
                        <ArrowUpRight size={13} />
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            </section>
          ) : null}
        </article>
      </main>

      <Footer />
    </SiteShell>
  )
}