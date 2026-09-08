# Sequential Plant Profile Automation

## Scope

This milestone adds a bounded authenticated workflow for creating new Plant
profile drafts. It uses the existing FastAPI modular monolith, PostgreSQL
models, editorial review state machine, public Plant API, and explicit
publication action. The shared Editorial Desk presents this workflow beside the
Discovery workflow at `/admin/pipelines`. It does not approve content, publish
content, or require a hosted/local LLM.

The version-controlled catalogue is
`backend/app/domains/encyclopedia/plant_pipeline_catalog.json`. It contains 25
vetted packages: Yarrow, Hop, Horse chestnut, Bearberry, Centaury, Yellow
gentian, Meadowsweet, Stinging nettle, Raspberry, Artichoke, Bilberry, Elder,
European goldenrod, Marshmallow, Ivy, Arnica, Eucalyptus, Cowslip, Heartsease,
Witch hazel, Butcher's broom, Java tea, Chaste tree, Guarana, and Silver birch.
Candidate identities, source packages, and exact capacity are backend-only until
a draft is persisted.

To extend it safely, add one candidate identity and one matching source package;
record the accepted Kew taxon and synonyms; supply authoritative evidence,
traditional-use limitations, safety, and distribution fields; add a new isolated
Commons photograph with creator, license URLs, dimensions, source URLs, and
SHA-256; then run catalogue, eligibility, media, and full pipeline tests. The
catalogue loader rejects missing packages, unsupported source registries,
incomplete article fields, invalid map data, non-photographic or undersized
media, unsafe paths, disallowed licenses, raster metadata mismatches, and
checksum mismatches.

The catalogue is finite. A protected reserve of ten ready, eligible candidates
must remain after every accepted launch. An exact 1-10 launch is rejected
atomically if it would cross that boundary; `All available` means only the safe
surplus and is capped at ten. Release readiness requires at least twenty eligible
candidates before a full ten-item run. Exhaustion stops safely instead of
inventing or recycling a Plant, and frontend payloads disclose neither capacity
nor future identity.

## Agent and stage boundaries

The orchestrator retains exact specification names where responsibilities
match:

1. **Normalization and Deduplication** — canonical identity comparison
   against profiles, revisions, explicit structured Discovery botanical
   subjects, and prior candidate reservations.
2. **Collector Gateway** — validates the bounded free-source package and
   provenance coverage.
3. **Botanical Resolver** — verifies the accepted taxon and stable identifier.
4. **Evidence, Safety, and Provenance** — requires overview provenance,
   evidence limitations, and safety coverage.
5. **Media & Geography Agent** — validates ISO country data plus licensed
   photographic raster metadata, dimensions, isolated path, and checksum.
6. **Content Composer** — assembles the existing structured Plant article
   contract without establishing botanical or safety truth.
7. **Editorial QA** — evaluates deterministic gates. It is not an AI score.
8. **Private review creation** — a persistence stage, not an autonomous agent.

The Publisher is intentionally absent from pipeline execution.

## Durability and sequence

`PipelineRun`, `PipelineStageResult`, `PlantPipelineItem`, and the shared
`PipelineBotanicalReservation` persist run, candidate, stage, timestamp, retry,
safe-message, quality-gate, output, lease-owner, and botanical-identity state. A
partial unique PostgreSQL index permits only one running editorial generation
run across Plant automation, Discovery automation, and the retained PubMed
runner. Globally unique normalized identity reservations and canonical Plant
identity indexes provide database protection against cross-domain races.

The start transaction validates the entire requested 1-10 batch against the
protected reserve, inserts the run and distinct ordered items, reserves all
identity keys, and commits a lease before responding. `All available` selects
the safe surplus above the reserve, capped at ten. It never silently plans a
partial request.

A bounded FastAPI background task executes after the HTTP response. It opens
fresh sessions at persisted stage boundaries and processes candidates in strict
ordinal order; the policy remains fail-fast. An idempotency-key replay returns
the same run. Browser polling is read-only, and refreshing, navigating away, or
closing the browser does not stop healthy execution.

The FastAPI lifespan also runs a recovery supervisor. On process start it claims
only queued or lease-expired Plant/Discovery runs with PostgreSQL row locks,
assigns a new lease owner, resets only the interrupted running stage, and resumes
at the first incomplete committed boundary. A fresh lease is never stolen and a
stale executor cannot persist after ownership changes. Replaying a recovery
claim creates no duplicate profile, review, source, item, or botanical
reservation. Held and failed runs remain terminal unless an authenticated owner
uses the explicit retry action.

Work necessarily pauses while the single web process is absent, then resumes
when its replacement starts and the old lease has expired. This is automatic
restart recovery, not a zero-downtime queue or worker guarantee. No database
transaction remains open across network work. Candidate data and media are
packaged in the application image; build validation resolves the same assets
from the production `frontend/dist` layout, so execution has no developer-machine
or runtime-download dependency.

## Eligibility rule

Identity values are Unicode-normalized, case-folded, and stripped of whitespace
and punctuation. Matching covers stable taxon identifier, accepted scientific
name, scientific synonyms, common names, existing Plant aliases, profile
revision payloads, explicit structured Discovery botanical identities, and
prior pipeline reservations. Discovery-to-Plant relationships are covered by
the related canonical Plant identity.

Incidental article prose is deliberately not searched: it is not a reliable
declaration that the article represents that botanical subject. Eligibility is
checked for preview, within the selected batch, and transactionally again
immediately before draft persistence.

## Editorial and public boundary
## Public ordering

Published Plant and Discovery archives order by `published_at DESC`, then stable
record ID ascending, before filtering pagination slices are returned. The homepage
Reviewed medicinal plants and secondary New evidence, carefully read sections use
that API order. Private, held, rejected, and approved-but-unpublished content stays
excluded. The hero Discovery carousel remains separately curated to its existing
three pinned slugs, order, images, controls, and Amla exclusion behavior.


Successful execution creates a `needs_review` Plant profile and
`EditorialReview` with source links and deterministic quality gates. The
public Plant endpoints still query published profiles only. Approval remains
an authenticated human action and publication remains a later explicit action.
The review UI prominently exposes the selected image, attribution, licensing,
sources, safety language, and pipeline gates.

## Editorial Desk presentation

`/admin/pipelines` contains one coordinated two-column section for Plants and
one for Discoveries. A genuinely fresh browser session leaves both quiet result
regions empty. The browser stores only a run ID that it launched, allowing a
refresh to recover that persisted active run without loading unrelated history.
While running the panel shows only a discreet status and adds a linked name only
after its private draft exists. After completion it shows only that run's linked
draft names and compact editorial statuses. Future candidates, capacity,
scientific identifiers, gates, counters, stages, and historical results are not
returned or rendered. Detailed diagnostics remain on `/admin/runs`; the former
`/admin/plant-pipeline` URL redirects to the canonical page.
