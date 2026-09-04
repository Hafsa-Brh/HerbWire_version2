# ADR-0004: Materials & Craft is a separate curated public domain

# Status

Accepted

# Date

2026-09-03

# Context

HerbWire already publishes medicinal Plant Profiles and evidence-qualified Discovery Briefs. Material culture stories need different fields, editorial structure, and claims: they concern natural materials, making practices, tools, vessels, and supported cultural context rather than plant monographs or medical research reports. Treating them as either existing domain would blur provenance and safety boundaries.

# Decision

Materials & Craft is HerbWire's third curated, public, PostgreSQL-backed content domain.

- It is non-medical and must not provide medical treatment claims or impersonate a Plant Profile or Discovery Brief.
- The current bounded milestone uses a deterministic, schema-validated curated corpus and idempotent importer.
- Each story stores structured article sections, stable identity and version, publication metadata, institutional source provenance, and licensed local media metadata with checksum.
- Public list and detail APIs return published Material Stories.
- Collection automation may be added later through the canonical source, review, and publishing boundaries; this decision does not activate an autonomous Materials pipeline.
- The combined Media & Geography Agent remains planned/postponed. Existing curated media and maps are not agent-produced runtime telemetry.

# Consequences

- Material Stories have a small dedicated persistence and API boundary while reusing canonical source records and the shared public shell.
- Dashboard and source catalogue totals include genuine Material Story records and relationships.
- Rolling back this feature requires removing its routes and UI, downgrading the dedicated tables, and removing only the seven local material media assets; Plant Profiles, Discovery Briefs, and their editorial state are unaffected.
- Source and media validation are required before corpus import.

# Alternatives considered

- Store stories as Plant Profiles: rejected because material culture articles are not taxon profiles.
- Store stories as Discovery Briefs: rejected because they are static non-medical material narratives, not research-news events.
- Present an unpersisted frontend mockup: rejected because the demo must use the real API and PostgreSQL.
- Activate Agent 9 for presentation: rejected because curated assets do not establish operational agent execution.

# References

- docs/specs/HERBWIRE_SPEC.md
- PLANS.md
- AGENTS.md