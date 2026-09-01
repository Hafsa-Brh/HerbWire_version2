# HerbWire V2 Execution Plans

## Rules

- Only one milestone may be active at a time.
- Every milestone must produce a demonstrable, tested result.
- Do not implement future agents as placeholders.
- Update this file when scope, decisions, blockers, or verification changes.
- Detailed product and architecture requirements live in
  `docs/specs/HERBWIRE_SPEC.md`.

## Current status

Project phase: Milestone 1 complete
Active milestone: None
Governance baseline status: Milestone 0 completed and merged into `main`
Authoritative specifications: Present
Initial ADRs: Accepted
Premature placeholders: Removed
Deployment status: Heroku approval pending
Heroku resources created: None
Heroku deployment and billing operations in this milestone: Not authorized
Zyte status: Student account activated but not integrated
Production secrets configured: No
Active branch: `feat/milestone-1-walking-skeleton`
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