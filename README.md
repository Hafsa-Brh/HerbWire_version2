# HerbWire V2

HerbWire V2 is an English-only medicinal-plant encyclopedia and traditional-medicine editorial platform. It preserves source provenance, keeps traditional-use documentation distinct from clinical efficacy, surfaces safety information, and requires explicit human approval before publication.

HerbWire does not diagnose, prescribe, recommend personalized treatment, provide dosage guidance, or present traditional use as proven clinical efficacy.

## Milestone 2 and 2B scope

Milestone 2 and 2B provide:

- PostgreSQL-backed plant profiles, provenance records, editorial reviews, pipeline runs, and pipeline stage results.
- Public homepage, paged plant index, published plant articles, and an honest New Discoveries empty state.
- A backend-authenticated local editorial desk with review, approval, hold/reject, and publication gating.
- Published-article Flashes and persisted pipeline-stage performance views.
- An idempotent newsletter subscription endpoint and database table. No external email provider is connected.
- A deterministic, schema-validated 30-profile encyclopedia corpus importer that preserves human editorial state and never auto-publishes.

Production authentication, deployment, RAG, and live Zyte collection are not included.

## Local setup

Run commands from the repository root unless a command says otherwise.

Create an ignored `.env` from `.env.example` and replace the placeholder database and local editorial authentication values. Never commit `.env`.

Start PostgreSQL and apply forward migrations:

```powershell
docker compose config
docker compose up -d postgres
docker compose ps
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

Seed the original curated review profiles only when a pre-Milestone 2B local database is missing them:

```powershell
.\.venv\Scripts\python.exe -m backend.app.workers.seed_curated_plants
```

Validate and import the Milestone 2B encyclopedia corpus in deterministic batches. Importing it again is idempotent and preserves approved/published article content and editorial status:

```powershell
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus --validate-only
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus --batch A
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus --batch B
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus --batch C
```

See [Encyclopedia corpus operations](docs/encyclopedia-corpus.md) before adding or updating a profile.

Start FastAPI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Start Vite from `frontend/`:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The API client aligns local loopback hostnames, so both `http://127.0.0.1:5173` and `http://localhost:5173` can use the HttpOnly editorial session correctly.

## Local URLs

- Homepage: `http://127.0.0.1:5173/`
- Plants: `http://127.0.0.1:5173/plants`
- Peppermint article: `http://127.0.0.1:5173/plants/peppermint`
- New Discoveries: `http://127.0.0.1:5173/discoveries`
- Login: `http://127.0.0.1:5173/login`
- Editorial dashboard: `http://127.0.0.1:5173/admin`
- API documentation: `http://127.0.0.1:8000/docs`

## Local editorial authentication

The local owner account is configured only through ignored server environment variables:

- `HERBWIRE_ADMIN_EMAIL`
- `HERBWIRE_ADMIN_PASSWORD`
- `HERBWIRE_SESSION_SECRET`

FastAPI validates the credentials and issues a signed HttpOnly, SameSite session cookie. Editorial endpoints require that session. The frontend does not store credentials or session secrets and does not use a local-editor header bypass. This is a local Milestone 2 authentication boundary, not production user management.

## Verification

Backend checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Frontend checks from `frontend/`:

```powershell
npm ci
npm run lint
npm run test
npm run typecheck
npm run build
```

The repository verification wrappers use only the disposable `herbwire_m2_migration_verify` database for destructive migration checks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

```bash
./scripts/verify.sh
```

## API surface

Public and authentication endpoints:

- `GET /api/v1/health`
- `GET /api/v1/version`
- `GET /api/v1/plants` (published-only paging, search, family, and diversity-tag filters)
- `GET /api/v1/plants/{slug}`
- `POST /api/v1/newsletter/subscriptions`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/session`

Authenticated editorial endpoints include review queue actions, approved-profile publication, pipeline runs, and agent-performance aggregation under `/api/v1/admin/`.

## External services

Zyte configuration names exist for a future approved integration, but ordinary Milestone 2B tests and runtime do not call Zyte. No Heroku or Zyte deployment is part of this milestone.
