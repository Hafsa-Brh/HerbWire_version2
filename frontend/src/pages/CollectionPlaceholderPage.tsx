import { Footer, SiteShell } from "../components/site/SiteShell"

export function CollectionPlaceholderPage({ title }: { title: string }) {
  return (
    <SiteShell>
      <main className="hw-container min-h-[55vh] py-16 md:py-24">
        <p className="hw-eyebrow">HerbWire collection</p>
        <h1 className="mt-3 max-w-3xl font-serif text-5xl font-semibold tracking-[-.055em] text-deep md:text-7xl">{title}</h1>
        <p className="mt-6 max-w-xl font-serif text-xl leading-relaxed text-muted">This HerbWire collection is being prepared.</p>
      </main>
      <Footer />
    </SiteShell>
  )
}
