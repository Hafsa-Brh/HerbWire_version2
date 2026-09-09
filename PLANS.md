# Professor-facing README refresh (2026-09-09)

Status: Complete; documentation-only change prepared on `main`.

## Intended outcome

Replace the milestone-centric README with a polished project overview that
explains HerbWire's public products, provenance and safety model, twelve logical
agents, keyword-based retrieval approach, Zyte collection boundary, Heroku
deployment architecture, local setup, verification commands, and key docs.

## Files expected to change

- `README.md`
- `PLANS.md`

## Risks and assumptions

- Product language describes the complete HerbWire architecture while retaining
  the mandatory human-publication and medical-safety boundaries.
- No application code, dependency, database state, credentials, or deployment
  resources change in this documentation-only task.

## Verification

Review Markdown structure, internal links, documented commands, repository diff,
and staged file scope before committing and pushing `main`.

# Pipeline corrections and restart recovery (2026-09-08)

Status: Complete and awaiting owner review on `feat/sequential-plant-pipeline`;
all work remains unstaged and uncommitted.

## Intended outcome

- Make both Pipelines result panels empty in a fresh browser session and show
  only persisted drafts from the run launched in that session: linked title and
  compact editorial status, plus a discreet running indicator while active.
- Centralize botanical identity matching across every Plant, revision,
  structured Discovery subject, explicit Plant relationship, and both pipeline
  reservation tables. Incidental prose remains outside the identity rule.
- Protect ten fully ready candidates per domain. Exact 1-10 launches are atomic
  and accepted only when the complete requested batch leaves that reserve;
  `All available` means the eligible surplus, capped at ten. Rejection creates
  no run or reservation and never exposes capacity or candidate identity.
- Package at least twenty currently eligible, source-complete candidates per
  domain so a clean full ten-item demonstration still leaves ten.
- Add startup recovery within the existing single-web-process modular monolith:
  claim only queued or lease-expired runs, resume at the first incomplete
  committed stage, and retain the existing manual retry only as a fallback.

## Expected changes

- Existing pipeline models, one additive Alembic revision after
  `20260907_0012`, a shared botanical-identity domain service, both bounded
  orchestrators/routes/schemas, and focused backend tests.
- The shared Pipelines page hook/result component and focused frontend tests.
- Both finite catalogue files plus isolated new licensed media files only.
- This plan and the existing Plant, Discovery, and deployment architecture
  documents. No unrelated public content or homepage-carousel code changes.

## Risks and assumptions

- Catalogue entries fail closed unless taxonomy, primary evidence, limitations,
  safety framing, geography, photographic licensing, dimensions, local path,
  and checksum all validate.
- A Heroku process cannot survive being killed; correctness comes from durable
  PostgreSQL stage boundaries and automatic recovery when the replacement web
  process starts. A fresh unexpired lease is never stolen.
- The protected owner database is read-only except for the later additive
  migration/runtime startup explicitly needed for final owner review. Existing
  drafts and editorial decisions are not altered.

## Verification gate

Focused eligibility/reserve/recovery and UI tests; full backend/frontend suites;
Ruff, ESLint, TypeScript, production build; fresh/0012/round-trip migrations and
Alembic drift; disposable ten-item plans and interrupted-process recovery;
corpus/media/carousel fingerprints; repository hygiene and a final diff review.

## Completion evidence for this correction

- The protected owner database upgraded additively from 0012 to 0013. Existing
  Plant, Discovery, source-link, review, Material, and pipeline-item counts and
  fingerprints were unchanged; only the `pipeline_runs` composite-row hash
  changed because 0013 adds the nullable lease-owner column.
- Read-only owner-state previews prove 20 eligible Plant candidates and 20
  eligible Discovery candidates. Each exact ten-item plan is accepted and leaves
  ten. Focused integration tests prove reserve-crossing rejection writes no run,
  item, reservation, draft, review, or source relationship.
- Both stale-boundary replay tests and separate replacement-Python-process tests
  passed for Plant and Discovery recovery. Replaying a completed recovery claim
  leaves draft, review, source, event/link, item, and reservation counts unchanged.
- Backend: Ruff check and format check passed; 171 tests passed (two upstream
  deprecation warnings). Frontend: ESLint and TypeScript passed, 53 tests passed,
  and the production build passed. The production Dockerfile built successfully
  and validated all 25 Plant and 20 Discovery packages from the dist-only image
  layout.
- Migration verification passed fresh-to-head, 0012-to-0013,
  0013-to-0012-to-0013, and Alembic drift check. Disposable databases and the
  temporary verification image were removed afterward.
- The carousel component remains byte-identical at SHA-256
  `af87603285879252a2dbc91c8169858f1ea6613a9e2172b6d456c46c94a69e98`.
  Browser automation could not start because its Windows sandbox failed before
  connection, so subjective viewport acceptance remains for the owner.
# Unified Plant and Discovery Pipelines (2026-09-07)
Status: Complete and awaiting owner review on `feat/sequential-plant-pipeline`.



- Preserve the verified dirty Plant milestone and protected owner-review data while replacing the single-purpose desk surface with one canonical authenticated `/admin/pipelines` page. `/admin/plant-pipeline` redirects to it, and detailed run history remains solely on Pipeline Runs.
- Reuse the existing PubMed collection contracts, normalization/deduplication rules, rich curated Discovery contract, source/event/article/review persistence, and human publication state machine. Add only a bounded version-controlled set of vetted PubMed source packages and a persisted sequential Discovery batch orchestrator.
- Use the existing one-web-process background model for both domains: one click starts a complete bounded batch, polling is read-only, every stage commits, and PostgreSQL enforces one active editorial generation run across Plant and Discovery domains. The later 2026-09-08 correction adds automatic expired-lease recovery.
- Keep upcoming Plant and Discovery identities backend-only. The later 2026-09-08 correction also removes exact capacity from frontend responses; generated titles become visible only after persistence.
- Restore the Plant release-readiness reserve to at least ten eligible packages in the protected owner-review state by adding source-complete Kew/EMA/Commons candidates. The finite catalogue stops honestly when exhausted.
- Verification covers migrations from `20260907_0011`, cross-pipeline concurrency, sequencing/idempotency/recovery, private Discovery creation, complete backend/frontend suites, unchanged public-content fingerprints, and exact homepage-carousel preservation.

### Expected continuation changes

- `PLANS.md`, `README.md`, `docs/architecture/DISCOVERY_4A.md`,
  `docs/architecture/SEQUENTIAL_PLANT_PIPELINE.md`, and the affected local-runtime
  note in `docs/architecture/DEPLOYMENT.md`.
- One additive Alembic revision after `20260907_0011`, focused shared pipeline
  item/API/orchestrator code, two fully validated Plant catalogue packages, and
  their isolated new licensed photographs.
- A canonical `PipelinesPage` with reusable typed section primitives, admin
  route/navigation updates, and focused backend/frontend tests.

### Risks and assumptions

- In-process background work is honest but not durable across a web-process
  restart; persisted stage boundaries and explicit retry are the recovery path.
- The Discovery automation catalogue is finite and deliberately small. It uses
  verified PubMed metadata/source extracts and existing licensed Plant media;
  it does not turn arbitrary live search results into finished articles.
- Existing owner editorial decisions are authoritative even where they changed
  after the prompt snapshot; implementation and tests must not rewrite them.

### Completion evidence

- Additive migration `20260907_0012` passed fresh upgrade, 0011 upgrade,
  downgrade/upgrade round trip, and Alembic drift checks in the disposable
  database.
- Backend suite passed 165 tests. Frontend passed 53 tests, ESLint, TypeScript,
  and the production build.
- The protected owner database retained 35 published Plants, 30 published
  Discoveries, seven Materials, and four preserved Plant runs. One new
  successful Discovery run created one private review draft and no public row.
- Published-corpus fingerprints and the curated carousel SHA-256 remained
  unchanged. Browser automation could not connect because the local browser
  harness was unavailable; owner visual review remains required.


# Sequential Plant Pipeline corrections (2026-09-07)

- Proven cause: the only multi-profile owner run requested two after Yarrow and Hop had consumed two of the three vetted candidates. The run truthfully stored one selected candidate but the UI allowed an ambiguous launch. This was catalogue exhaustion plus unclear partial-batch semantics, not a sequential-loop defect.
- Expand the bounded catalogue with ten Kew/EMA/Commons-verified candidates, expose total vetted and currently eligible capacity, accept 1-10 or all available, and require explicit consent before planning fewer candidates than requested.
- Reserve the complete batch transactionally, persist requested/available/planned/completed/held/failed/remaining counts, and execute all candidate stages sequentially in one in-process FastAPI background task with fresh database sessions per step. Polling becomes read-only. A process restart may interrupt execution; persisted leases and explicit retry safely resume from the failed boundary.
- Order public Plant and Discovery archives by `published_at DESC` with stable ID tie-breaking before pagination. Feed the homepage Plant and secondary Discovery sections from that order while pinning the existing three hero-carousel Discovery slugs and order.
- Add focused backend/frontend regressions for capacity, partial consent, all-available selection, batches through ten, sequential timing, polling independence, recovery/idempotency, newest-first ordering, private exclusion, homepage selection, and exact carousel preservation.

# HerbWire V2 Execution Plans

## Sequential Plant Profile Automation

Status: Complete and awaiting owner review on `feat/sequential-plant-pipeline`

### Intended outcome

Add an authenticated Editorial Desk page named **Plant Pipeline** that creates
one to ten, or all available, genuinely new source-led Plant drafts in strict sequence.
Every successful candidate ends as a private `needs_review` Plant and existing
editorial review item. The pipeline never approves, promotes, publishes, or
changes existing public content.

### Inspected baseline and design

- Start point: clean `main` at `630f97c137485a310477a16e6b94e66a9634113c`;
  local `main` and the local `origin/main` tracking ref matched before branching.
- The existing 30 Plants are validated deterministic corpus imports. A new Plant
  follows the established canonical private draft plus `EditorialReview` path;
  `PlantProfileRevision` remains reserved for proposals against an existing Plant.
- Existing `PipelineRun` storage is reused. An additive migration supplies
  candidate ordinals, stage timestamps/running state, per-run candidate items,
  resumable leases, database-enforced single-active-run protection, and final
  accepted-taxon/scientific-name race protection.
- The one-web-process deployment starts a bounded in-process background task;
  read-only polling reports database-persisted progress. No worker, scheduler,
  queue, paid API, hosted LLM, or new service is introduced.
- Exact per-candidate order: `Normalization and Deduplication`,
  `Collector Gateway`, `Botanical Resolver`,
  `Evidence, Safety, and Provenance`, `Media & Geography Agent`,
  `Content Composer`, `Editorial QA`, then the persistence stage
  `Queue editorial review`.
- Execution is strictly sequential and fail-fast after a recorded failure/hold.
  Every stage boundary commits. Closing or refreshing the desk does not stop a healthy
  task. A web-process restart interrupts in-memory execution; persisted leases and the
  authenticated Resume/Retry action recover the same run at a safe stage boundary.

### Ordered work

1. Add a small candidate-key catalogue, separately validated source packages,
   and new licensed candidate photographs without changing existing media.
2. Centralize Unicode/name/synonym/taxon eligibility across Plants, revisions,
   explicit Discovery botanical subjects and relationships; ignore incidental prose.
3. Add the additive migration and typed stage/orchestrator contracts.
4. Add authenticated preview/current/start/advance/retry/read admin endpoints.
5. Add the responsive **Plant Pipeline** desk page and review quality-gate panel.
6. Add unit, integration, API, migration, frontend, and corpus regression tests.
7. Update README/deployment architecture, run safe verification, and review diff.

### Files expected to change

- `PLANS.md`, `README.md`, `docs/architecture/DEPLOYMENT.md`, and one focused
  pipeline architecture note under `docs/architecture/`.
- One Alembic revision, `backend/app/models/encyclopedia.py`, focused modules
  under the existing encyclopedia/pipeline domains, and admin routes/schemas.
- A small encyclopedia candidate/source-package data set and new files only under
  `frontend/public/media/plants/` for candidate photos.
- Existing frontend admin API/routing plus one focused Plant Pipeline page.
- Focused backend/frontend tests. Homepage carousel implementation is untouched.

### Risks and assumptions

- Deterministic curated source packages are required for a reliable one-web demo;
  provider failures remain explicit and testable, but no durable unattended work
  is claimed while the owner is absent.
- Source, media, safety, and eligibility checks fail closed. Pipeline success
  means private review readiness only.
- Activating the previously postponed Media & Geography Agent is within this
  explicitly approved milestone because it performs genuine validation.

### Verification and recovery

Run backend Ruff/format/tests, frontend lint/typecheck/tests/build, migration
fresh/upgrade/downgrade/check, disposable pipeline/concurrency/idempotency tests,
public corpus fingerprints/counts, and responsive local runtime checks. All work
remains unstaged/uncommitted. The additive downgrade removes only new pipeline
state and restores the previous stage constraint.

### Best next action

Finish implementation and disposable verification, then leave the safe local
review runtime running for owner inspection without deploying, committing, or
pushing.


## Rules

- Only one milestone may be active at a time.
- Every milestone must produce a demonstrable, tested result.
- Do not implement future agents as placeholders.
- Update this file when scope, decisions, blockers, or verification changes.
- Detailed product and architecture requirements live in
  `docs/specs/HERBWIRE_SPEC.md`.

## Production Material media import hotfix

Status: Ready for owner review on `fix/material-media-production-import`

### Goal

Make curated Material media validation resolve the same pinned, repository-owned
image bytes from both the source checkout (`frontend/public`) and the compiled
production runtime (`frontend/dist`) without changing content or weakening
checksum validation.

### Boundaries

- No production access, deployment, migration, import, rollback, or configuration.
- No changes to licensed media bytes, corpus metadata, Plant content, or Discovery
  content.
- Reject path traversal and fail closed for missing or checksum-mismatched media.

### Verification required

Reproduce the failure in the unmodified production image; add source/runtime,
checksum, missing, changed, traversal, and working-directory regression tests;
run complete backend/frontend checks; build the exact production image; validate
all seven runtime files and importer idempotency against a disposable database;
review the final unstaged diff and repository hygiene.

### Verified locally

The unchanged image reproduced all seven failures while the files and checksums
were present under `frontend/dist`. Focused tests, 143 backend tests, 50 frontend
tests, linting, type checking, production builds, the final-image media gate, and
disposable 7/0/15/15 then 0/7/0/0 importer runs passed.

## Pipeline publication and newest-first correction

Status: Ready for owner review on fix/pipeline-publication-and-ordering

The pipeline intentionally persists automated Discovery origin while publication
currently accepts only curated origin. Validate automated origin through persisted
pipeline ownership and successful quality gates without admitting synthetic or
unowned content. Show real publication dates on Plant archive cards, preserve
database-level newest-first ordering, and keep the curated homepage Discovery
carousel byte-identical.

No schema change is expected. Use disposable PostgreSQL data and preserve all
owner records and editorial decisions.

## Demo Materials & Craft curated-domain increment

Status: In progress and awaiting owner visual review

### Goal

Add seven authoritative, licensed-media, database-backed Materials & Craft stories as HerbWire's third curated public domain; refine the real-data homepage carousel; align Plants Review and Discovery Review structure; and keep the combined Media & Geography Agent visibly planned rather than presenting curated assets as runtime output.

### Boundaries

- Deterministic curated corpus and public list/detail APIs only.
- No autonomous Materials pipeline and no activation of Agent 9.
- No mutation of existing plant or discovery content or editorial state.
- No deployment, push, or Heroku action during owner visual review.

### Verification required

Corpus validation, idempotent import and conflict rejection; migration upgrade/check/round trip; complete backend/frontend checks; unchanged plant/discovery fingerprints; seven working public stories and licensed local images; responsive owner review.
## Current status

Project phase: Milestone 1 complete
Active milestone: Demo Materials & Craft curated-domain increment
Governance baseline status: Milestone 0 completed and merged into `main`
Authoritative specifications: Present
Initial ADRs: Accepted
Premature placeholders: Removed
Deployment status: Heroku approval pending
Heroku resources created: None
Heroku deployment and billing operations in this milestone: Not authorized
Zyte status: Student account activated but not integrated
Production secrets configured: No
Active branch: feat/demo-frontend-enhancement
Application implementation status: Walking skeleton implemented and fully runtime-verified

## Milestone 1 - Deployable walking skeleton

Status: Complete

### Goal

Create the smallest frontend, API, health endpoint, PostgreSQL
connection, migration, tests, and deployment-neutral CI foundation.

### Restrictions

- No collection or article generation yet.
- No Heroku deployment or billing operations.
- No Zyte integration.

### Verified in this checkout on Saturday, August 29, 2026

- `docker compose config` passed.
- `docker compose up -d postgres` succeeded with the canonical local PostgreSQL host port defaulting to `5433`.
- PostgreSQL 17 reached Compose health `healthy` on `127.0.0.1:5433`.
- The Alembic `current`, `upgrade -> downgrade -> upgrade` cycle completed successfully against the Compose PostgreSQL instance.
- The live PostgreSQL schema contains the `sources` table with the expected columns, primary key, and unique constraint `uq_sources_identifier`.
- Backend checks passed:
  - `ruff check`
  - `ruff format --check`
  - `pytest` with 6 passing tests, including 1 integration test
- Frontend checks passed:
  - `npm run lint`
  - `npm run test` with 5 passing tests in 1 file
  - `npm run typecheck`
  - `npm run build`
- The canonical Vite development port remains `5173`.
- The successful manual browser verification used the temporary explicit override port `4173` because `5173` was occupied at that time.
- `GET /api/v1/version` returned HTTP `200` with the expected JSON payload.
- `GET /api/v1/health` returned HTTP `200` with `database=connected` while PostgreSQL was running.
- After stopping only the HerbWire PostgreSQL container, `GET /api/v1/health` returned HTTP `503` with `database=disconnected` and no leaked internal details.
- After restarting PostgreSQL, `GET /api/v1/health` recovered to HTTP `200` with `database=connected`.
- The backend accepted CORS requests from the configured frontend origin.
- The frontend runtime path targets the live backend health endpoint and does not use fake local health data.
- Final manual browser verification passed in connected, degraded, and recovered states without visible layout failure, blank rendering, React errors, CORS issues, or uncaught exceptions.
- Opening `http://127.0.0.1:8000/` returned the expected FastAPI `404` because no root route is defined.
- The repository verification wrappers passed after being aligned with the verified local database configuration.

### Remaining mandatory runtime checks

- None. Milestone 1 acceptance is complete.

### Current blocker

- None for Milestone 1 closeout.

### Files expected to change to finish Milestone 1

- None required for Milestone 1 completion.

### Best next action

Review the final diff and approve the commit for the completed Milestone 1 branch.

## Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-08-29 | Start with seven essential logical agents | Provides a complete workflow without unnecessary modules |
| 2026-08-29 | Postpone RAG | No curated corpus or measured retrieval requirement yet |
| 2026-08-29 | Use deterministic fixtures before Zyte | Makes failures reproducible |
| 2026-08-29 | Wait for Heroku approval | Avoid premature provider-specific work |
| 2026-08-29 | Defer Milestone 0 status finalization until the first controlled Milestone 1 change | Preserved a clean governance merge while keeping the branch transition explicit |
| 2026-08-29 | Keep Vite default development port at `5173` | Preserves the standard repository default while allowing explicit overrides when local conflicts exist |
| 2026-08-29 | Use local PostgreSQL host port default `5433` | Port `5432` was already occupied by an unrelated local process, and HerbWire must not disrupt unrelated services during verification |
| 2026-08-29 | Add a bounded PostgreSQL connect timeout in the backend engine configuration | Ensures `/api/v1/health` can return a prompt degraded `503` when the database is unavailable |
| 2026-08-29 | Complete manual browser verification for Milestone 1 with temporary frontend port override `4173` | Confirmed the real React -> FastAPI -> PostgreSQL UI flow in connected, degraded, and recovered states without adding a root route |