# HerbWire V2

HerbWire V2 is an English-only medicinal-plant encyclopedia and traditional-medicine discovery platform. It is intended to collect international source material, preserve provenance, produce structured English drafts, apply botanical, evidence, and safety checks, and require explicit human approval before any public publication.

HerbWire does not diagnose, prescribe, recommend personalized treatment, provide dosage guidance, or present traditional use as proven clinical efficacy.

## Current status

This repository has completed the Milestone 1 walking skeleton on `feat/milestone-1-walking-skeleton`.

- No deployment exists.
- Heroku approval is pending and untouched.
- No Heroku resource has been created.
- A Zyte student account is activated, but Zyte is not integrated into this repository.
- Static checks, backend tests, frontend tests, frontend typecheck, frontend build, backend/frontend local process startup, and the final manual browser verification have been verified in this checkout.
- PostgreSQL local development defaults to host port `5433`.
- Vite's canonical repository development port remains `5173`.
- The successful manual browser verification used a temporary explicit frontend override on port `4173` because `5173` was occupied at that time.

## Verified commands

Run these from `C:\Users\PC\Documents\ChatGPT\HerbWire_version2` unless otherwise noted.

### Canonical local runtime setup

Backend, from the repo root:

```powershell
$env:HERBWIRE_FRONTEND_ORIGIN='http://127.0.0.1:5173'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Frontend, from `frontend/`:

```powershell
$env:VITE_HERBWIRE_API_BASE_URL='http://127.0.0.1:8000'
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

PostgreSQL, from the repo root:

```powershell
docker compose config
docker compose up -d postgres
docker compose ps
```

### Temporary manual verification override used successfully on Saturday, August 29, 2026

Backend, from the repo root:

```powershell
$env:HERBWIRE_FRONTEND_ORIGIN='http://127.0.0.1:4173'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Frontend, from `frontend/`:

```powershell
$env:VITE_HERBWIRE_API_BASE_URL='http://127.0.0.1:8000'
npm run dev -- --host 127.0.0.1 --port 4173 --strictPort
```

### Regression commands

Backend checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini downgrade base
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

Frontend checks, from `frontend/`:

```powershell
npm run lint
npm run test
npm run typecheck
npm run build
```

Repository verification wrappers:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

```bash
./scripts/verify.sh
```

## Integration-test database requirement

- Backend integration tests use the migrated PostgreSQL development or CI database.
- They do not use `create_all` and rely on Alembic having created the `sources` table and its uniqueness constraint.
- Local integration tests require PostgreSQL to be running on the configured local host port, which defaults to `5433` in this repository.

## Verified runtime behavior

- `GET /api/v1/version` returned HTTP `200` with JSON `{"service":"herbwire-api","version":"0.1.0"}`.
- `GET /api/v1/health` returned HTTP `200` with JSON `{"status":"ok","service":"herbwire-api","version":"0.1.0","database":"connected"}` while PostgreSQL was connected.
- `GET /api/v1/health` returned HTTP `503` with JSON `{"status":"degraded","service":"herbwire-api","version":"0.1.0","database":"disconnected"}` while PostgreSQL was stopped.
- `GET /api/v1/health` recovered to HTTP `200` with `database="connected"` after PostgreSQL restarted.
- CORS allowed the configured frontend origin.
- The frontend runtime path targets the live backend health endpoint at `${getApiBaseUrl()}/api/v1/health` and does not use fake local health data.
- Manual browser verification confirmed the UI rendered the expected connected, degraded, and recovered states without visible layout failure, blank rendering, React errors, CORS issues, or uncaught exceptions.
- Opening `http://127.0.0.1:8000/` returned the expected FastAPI `404` because no root route is defined, and that behavior remains intentional.

## Milestone 1 acceptance

- All Milestone 1 acceptance checks passed, including the final manual browser verification.
- The backend root path `/` intentionally remains undefined and returns HTTP `404`.

## Authoritative documents

- `docs/specs/HERBWIRE_SPEC.md`
- `PLANS.md`
- `AGENTS.md`
- `docs/decisions/`
- `docs/reference/HerbWire_V2_Functional_Technical_Specification_v1.0.docx`