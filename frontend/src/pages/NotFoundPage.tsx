import { Footer, SiteShell } from "../components/site/SiteShell"
import { RouteState } from "../components/site/RouteState"

export function NotFoundPage() {
  return (
    <SiteShell>
      <main id="top">
        <RouteState eyebrow="HerbWire / not found" title="This page slipped out of the wire." description="The page you were looking for is not available here. The encyclopedia is still intact." primaryAction={{ label: "Return home", to: "/" }} secondaryAction={{ label: "Browse plants", to: "/plants" }} />
      </main>
      <Footer />
    </SiteShell>
  )
}