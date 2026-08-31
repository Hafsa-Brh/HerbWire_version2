# HerbWire V2 Execution Plan

## Active milestone

Milestone: 2B - Production-quality encyclopedia corpus
Branch: `feat/milestone-2b-encyclopedia-corpus`
Status: Runtime verification in progress
Started: 2026-08-31

## Goal

Expand the curated encyclopedia from three profiles to at least 30
schema-validated, provenance-linked, safety-qualified English profiles in
PostgreSQL. New profiles enter editorial review and are never published
automatically.

## Non-goals

- No New Discoveries collection or scheduling.
- No Zyte access.
- No RAG or runtime model generation.
- No deployment.
- No paid APIs.
- No automatic editorial approval or publication.
- No frontend redesign.

## Verified baseline

- The branch is clean and exactly based on fetched `origin/main` at
  `6b81f99b86cc8f113bf7eb60b4bda342c1a1bbdc`.
- PostgreSQL 17 is healthy on host port `5433`.
- The main `herbwire` database is at the single Alembic head
  `20260831_0004`.
- PostgreSQL contains 3 plant profiles: 2 published and 1 `needs_review`.
- It contains 10 source records, 4 source registry rows, 3 reviews, and 9
  profile-source links.
- Existing media and distribution are unvalidated JSON fields. Images are
  local placeholders, and distribution has no native/introduced status.

## Ordered work

1. Audit current models, APIs, seed behavior, frontend fields, and tests.
2. Verify a geographically diverse 30-plant candidate manifest against
   authoritative taxonomy, traditional-use/safety, distribution, and media
   sources; hold candidates that do not meet the evidence or licensing bar.
3. Add one coherent forward schema migration for narrowly scoped taxonomy,
   media, distribution, and readiness data.
4. Replace inline corpus data with schema-validated, deterministic source
   files and an idempotent, update-safe importer that preserves human state.
5. Process and verify corpus batches A, B, and C in a disposable database
   before forwarding accepted rows to the main local database.
6. Extend public APIs with paging/search/filtering and complete article
   contracts while preserving published-only enforcement.
7. Extend the editorial API and desk with completeness indicators, readiness
   warnings, filters, media attribution, and distribution preview.
8. Extend the existing approved public UI without changing its visual system.
9. Verify migration downgrade/upgrade only in
   `herbwire_m2_migration_verify`, then upgrade the main database forward.
10. Run all backend/frontend gates and real runtime checks; leave services
    running for human review.
11. Document corpus, source, image, distribution, readiness, and safe import
    procedures; inspect the final diff and hygiene.

## Expected change areas

- `backend/app/models/encyclopedia.py`
- `backend/app/domains/encyclopedia/`
- `backend/app/api/routes/plants.py`
- `backend/app/api/routes/editorial.py`
- `backend/app/api/schemas.py`
- `backend/app/workers/seed_curated_plants.py`
- `backend/alembic/versions/`
- `backend/tests/`
- `data/fixtures/` or the existing approved fixture location
- `frontend/src/api/`
- `frontend/src/components/plants/`
- `frontend/src/pages/PlantsPage.tsx`
- `frontend/src/pages/PlantArticlePage.tsx`
- `frontend/src/pages/admin/`
- `frontend/src/App.test.tsx`
- `README.md` and narrowly scoped source/corpus policy documentation

## Risks and assumptions

- Exact taxonomy, safety wording, image identity, and reuse licensing require
  source-by-source verification; unsupported candidates will remain held.
- A high-quality licensed image may not be available for every candidate.
  Honest fallback records are allowed but do not count as fully complete.
- POWO rendered maps are not assumed reusable. HerbWire will store sourced
  structured regions and render only from a separately licensed boundary
  dataset; otherwise it will show an accessible text fallback.
- Existing published profiles and editorial decisions must survive imports.
- Source availability or licensing can reduce the accepted corpus below 30;
  that is a blocker, not permission to fabricate content.

## Acceptance criteria

- At least 30 profiles are stored without duplicate slugs, accepted names,
  citations, media checksums, or distribution rows.
- Every imported profile has verified taxonomy and traceable source coverage;
  new profiles remain `needs_review` or held.
- Public APIs expose only published profiles and support paging/search/filter.
- Editorial previews expose readiness, sources, safety, media, and
  distribution status.
- Licensed media includes source, creator, license, attribution, dimensions,
  checksum, and a present local asset; missing media is reported honestly.
- Migration and import idempotency checks pass in disposable databases.
- Backend Ruff and pytest pass; frontend lint, tests, typecheck, and build pass.
- Runtime verification proves PostgreSQL -> FastAPI -> React data flow.

## Recovery

No commit or push is authorized. Accepted migrations are never rewritten.
Destructive migration checks target only the disposable database after its
name is programmatically verified. The main database receives forward-only
upgrades and update-safe imports.

## Completed gates

- Thirty accepted taxa, 92 manifest sources, 30 licensed local images, and structured native/introduced distribution entries validate successfully.
- Disposable migration upgrade/downgrade/upgrade and three-batch import pass.
- Importing the complete corpus twice creates no duplicate profile, source, link, or media checksum.
- Main PostgreSQL is at `20260831_0005` with 30 profiles: 27 published and 3 held after human editorial actions.
- Public paging/search/filter, complete article metadata, and editorial completeness filters are implemented without changing the approved visual system.
- Static encyclopedia review now lives at `/admin/reviews` with a six-item paged queue; `/admin` is reserved honestly for future operational dashboards.
- All 30 profiles have source-reviewed country-level distribution maps derived from WCVP TDWG Level 3 records exposed through GBIF and mapped through official WGSRPD ISO cross-references. Textual botanical-region summaries remain authoritative.
- Backend and frontend automated gates have passed once on the implementation snapshot; final documentation/runtime/hygiene verification remains.

## Final editorial enrichment pass

1. Replace the synthesized, repetitive article overview with independently
   sourced background and a dedicated "How Much Do We Know?" evidence
   snapshot.
2. Enrich all 30 corpus records from their existing official NCCIH or EMA
   monographs, adding a second NCCIH source for peppermint where it directly
   supports the same accepted taxon.
3. Expand preparation/use context and safety cautions without dosage,
   prescribing language, or unsupported clinical claims.
4. Replace illustrations, herbarium sheets, and other unsuitable hero media
   with exact-taxon, explicitly licensed photographs.
5. Validate and import changes idempotently without changing review or
   publication states, then rerun all backend, frontend, database, runtime,
   secret, artifact, and diff checks.

The accepted profile rows remain protected from silent substantive overwrite.
Any revision to already published content must pass through the existing human
editorial workflow rather than weakening the publication gate.

## Current blocker

Twenty-seven profiles are already published. The version-3 source-led text
cannot be imported over those public rows without bypassing human review. A
pending-revision workflow, or another explicitly approved editorial transition,
is required before the enriched public text can be stored in the main database.

## Best next action

Approve and implement the pending-revision workflow so version-3 drafts can be reviewed while the current published versions remain public.

## Plants archive and corpus expansion follow-up

1. Remove the redundant Plants-page introduction and place the existing
   search/filter controls directly below the `MEDICINAL PLANTS` heading.
2. Keep licensed-image attribution at the article hero, but exclude
   `licensed_media` records from the claims-and-information Sources section.
3. Add an optional, structured, source-linked medicinal-product field only
   where an official regulatory or public-health source supports it.
4. Prepare three additional ten-profile corpus batches with the same taxonomy,
   safety, provenance, media, and distribution validation as the accepted
   thirty-profile corpus. New profiles remain review-gated.
5. Validate/import each new batch idempotently, then run focused and complete
   backend/frontend/database verification without publishing any new profile.

The pending-revision blocker still applies to substantive changes proposed for
the twenty-seven currently published rows. No importer may overwrite their
public content or bypass the editorial state machine.

## Pending profile revision workflow

### Outcome

Store newer corpus articles as reviewable revisions while the canonical published
profile remains unchanged. Reviewers compare complete current/proposed payloads,
approve or hold a revision, and explicitly promote only an approved revision in
one database transaction.

### Owned files

- `backend/app/models/encyclopedia.py` and one forward Alembic migration
- `backend/app/domains/encyclopedia/service.py`
- existing editorial schemas/routes and integration tests
- existing typed frontend API boundary, admin application, and frontend tests
- corpus operations documentation

### Risks and controls

- Published and otherwise protected profiles are never directly overwritten by
  import; newer manifest content creates one checksum/version-unique revision.
- Promotion snapshots the prior canonical payload for audit, applies the complete
  proposal atomically, and preserves public publication only for an already
  published profile.
- Held, failed, and unapproved revisions remain absent from public APIs.
- Migration downgrade testing targets only `herbwire_m2b_revision_verify`; the
  main database receives a forward upgrade only.

### Verification sequence

1. Prove migration upgrade/downgrade/upgrade and constraints in the disposable database.
2. Run importer and workflow integration tests, including idempotency and public exclusion.
3. Apply the forward migration and import version 3 as pending revisions locally.
4. Exercise peppermint v1 -> pending v3 -> approved -> promoted through authenticated HTTP.
5. Run complete backend/frontend gates, runtime checks, hygiene review, and commit without push.
