# Heroku staging deployment

## Scope and cost boundary

This runbook describes one personal Heroku application on the Cedar container
stack, one Eco web dyno, and one heroku-postgresql:essential-0 database. It
does not authorize provisioning. There is no worker, scheduler, pipeline,
review app, CI service, custom domain, Key-Value Store, or third-party add-on.

The maximum monthly list price is $10: the $5 Eco Dynos subscription plus one
$5 Essential-0 database. The GitHub Student offer provides $13 of applicable
platform credit per month; the remaining $3 is deliberately unused.

## Architecture

The Dockerfile builds the React application in a Node stage and copies only the
compiled output into a non-root Python runtime. FastAPI serves assets, the 30
committed plant images, and index.html for unknown frontend routes. Unknown API
routes remain API 404 responses. Browser API requests are relative and
therefore same-origin.

The Heroku manifest defines one image and one web process. Its release phase
runs only the Alembic upgrade to head. Web startup uses the backend web module,
binds 0.0.0.0 at Heroku's PORT, and trusts Heroku router forwarded headers.
Docker Compose is local-only.

## Audit conclusions

1. FastAPI can safely serve the compiled React application; the SPA fallback
   explicitly excludes all API paths.
2. Frontend requests use relative API URLs by default. Local Vite may still use
   VITE_HERBWIRE_API_BASE_URL.
3. The production web entry point validates and binds Heroku's PORT.
4. Settings accept DATABASE_URL, normalize the Heroku scheme for psycopg, and
   add sslmode=require in staging and production.
5. Alembic consumes the same normalized settings URL.
6. No migration or runtime module references pgvector or a vector extension.
7. No extension creation is required. Phase 2 verifies that fact and must not
   create an extension.
8. The committed manifest contains exactly 30 rich version-4 profiles and 30
   corresponding licensed local images.
9. The corpus importer is idempotent and preserves protected canonical rows.
10. A fresh import creates needs_review profiles; a newer version of a
    protected row creates a pending revision instead of overwriting it.
11. The staging-only bootstrap command imports and verifies all 30 records but
    deliberately does not approve or publish them.
12. Vite includes the committed images in the production build.
13. Runtime code has no dependency on local Windows paths.
14. Application runtime code does not write persistent files.
15. Editorial authentication is acceptable for a tightly scoped single-editor
    staging site after deployment validation and the login throttle.
16. No header bypass exists. The two development mutation endpoints return 404
    when development endpoints are disabled.
17. Credentials are backend-only config variables. They are not returned,
    logged, or bundled into frontend assets.
18. Staging requires a host-prefixed Secure, HttpOnly, SameSite=Lax cookie with
    an eight-hour default expiration. Logout deletes it; every editorial
    endpoint has the session dependency.
19. Unknown frontend routes return index.html; unknown API routes never do.
20. Runtime loads one Uvicorn worker, FastAPI, SQLAlchemy, and static files.
    Node and the Vite build are absent from the runtime image. This is suitable
    for the Eco 512 MB limit, subject to the local runtime measurement.

## Required config variable names

- DATABASE_URL (created and rotated by the Postgres add-on)
- HERBWIRE_ENVIRONMENT
- HERBWIRE_FRONTEND_ORIGIN
- HERBWIRE_ADMIN_EMAIL
- HERBWIRE_ADMIN_PASSWORD
- HERBWIRE_SESSION_SECRET
- HERBWIRE_SESSION_COOKIE_NAME
- HERBWIRE_SESSION_COOKIE_SECURE
- HERBWIRE_ENABLE_DEVELOPMENT_ENDPOINTS

Do not set VITE_HERBWIRE_API_BASE_URL in Heroku. Do not place a credential in
source, the Heroku manifest, Docker build arguments, shell history, or the
frontend bundle.

## Release and corpus order

1. Build the single linux/amd64 image.
2. Let the release phase run Alembic upgrade head. A failed migration prevents
   the new web release from starting.
3. Start exactly one Eco web process.
4. Check the health endpoint.
5. Run the explicit staging corpus bootstrap once as an Eco one-off command:

       heroku run python -m backend.app.workers.bootstrap_staging_corpus --confirm-review-required -a $HerokuApp

6. Run it a second time. The second result must show zero profiles created,
   zero source links created, zero revisions, and 30 review-ready profiles.
7. Sign in to the Editorial Desk. A human reviewer must inspect, approve, and
   publish each of the 30 profiles. The bootstrap cannot perform this step.
8. Confirm the public plant index contains 30 records and inspect representative
   profiles, provenance, media attribution, distribution, article details, and
   safety sections.

The importer commits before its verification checks and existing domain actions
commit per editorial decision. If bootstrap or review is interrupted, fix the
reported cause and rerun it; idempotency and protected-content rules make this
safer than attempting a database rollback. Never seed on web dyno startup.

## pgvector

No current migration requires pgvector, so neither the release phase nor
bootstrap creates the extension. Before provisioning, retain the current
no-vector code and migration scan. After migration, a read-only database
inspection may confirm that no vector column or extension is required. Adding
pgvector later requires the approved RAG milestone and its architecture review.

## Authentication

The staging owner credentials and session secret are backend-only config
variables. Startup fails unless the password is at least 16 characters, the
session secret is at least 32 characters, the cookie name has the __Host-
prefix, Secure cookies are enabled, the frontend origin is empty for
same-origin use, and development endpoints are disabled. Login failures are
limited to five attempts per client over five minutes in the single web
process. No local editor header is recognized.

The staging authentication is intentionally a single-owner boundary, not a
general production identity system. Do not add additional users or expose this
deployment as production without a separate authentication decision.

## Proposed Phase 2 provisioning sequence -- not executed

CLI is preferred for Phase 2 because every mutating operation and returned plan
must be inspected in order. Work only in the repository root after this branch
is reviewed and merged. Stop if the account is not personal, the student credit
is inactive, any app or pipeline already exists, or any displayed plan/price
differs from this runbook.

PowerShell:

    Set-Location C:\Users\PC\Documents\ChatGPT\HerbWire_version2
    git switch main
    git pull --ff-only origin main
    git status --short
    $HerokuApp = "<approved-unique-app-name>"
    heroku auth:whoami
    heroku apps
    heroku pipelines
    heroku apps:create $HerokuApp --region eu
    heroku stack:set container -a $HerokuApp
    heroku addons:create heroku-postgresql:essential-0 -a $HerokuApp
    heroku pg:wait -a $HerokuApp
    heroku config:set HERBWIRE_ENVIRONMENT=staging HERBWIRE_FRONTEND_ORIGIN="" HERBWIRE_SESSION_COOKIE_NAME=__Host-herbwire_editor_session HERBWIRE_SESSION_COOKIE_SECURE=true HERBWIRE_ENABLE_DEVELOPMENT_ENDPOINTS=false -a $HerokuApp

Before the first deploy, subscribe to Eco on the personal account Billing page.
Heroku documents that subscribed accounts default new apps to Eco; otherwise
they default to Basic. Then set the three backend-only secret values
HERBWIRE_ADMIN_EMAIL, HERBWIRE_ADMIN_PASSWORD, and HERBWIRE_SESSION_SECRET in
the app's Settings page. Do not put their values in a shell command or paste
them into a report.

Continue only after the Resources page shows one Essential-0 database, no other
add-on, and the account shows the Eco subscription:

    heroku git:remote -a $HerokuApp
    git push heroku HEAD:main
    heroku ps:type web=eco -a $HerokuApp
    heroku ps:scale web=1 -a $HerokuApp
    heroku ps -a $HerokuApp
    heroku addons -a $HerokuApp
    heroku releases -a $HerokuApp
    heroku run python -m backend.app.workers.bootstrap_staging_corpus --confirm-review-required -a $HerokuApp

Expected result: one Eco web process, one Essential-0 database, a successful
Alembic release, and 30 review-ready profiles. Paste back only command status,
plan names, counts, and HTTP results; never paste config output or credentials.
If the release fails, scale web to zero and inspect release/application logs:

    heroku ps:scale web=0 -a $HerokuApp
    heroku releases:output -a $HerokuApp
    heroku logs --tail -a $HerokuApp

Do not edit the same checkout concurrently while Phase 2 commands run.

## Rollback and zero-cost exit -- destructive commands not executed

Application rollback is forward-schema-safe only. Inspect releases, then:

    heroku releases -a $HerokuApp
    heroku rollback <previous-release> -a $HerokuApp

Database migrations are not automatically downgraded. Prefer a forward fix.
Before database or app destruction, stop writes, capture a logical backup, and
download it outside the repository:

    heroku ps:scale web=0 -a $HerokuApp
    heroku pg:backups:capture -a $HerokuApp
    heroku pg:backups:download -a $HerokuApp

Confirm that the downloaded dump exists and is protected. Destroying the
database permanently removes staging data; destroying the app removes the app,
releases, config, and attachments. Only after explicit destructive approval:

    heroku addons:destroy heroku-postgresql --confirm $HerokuApp -a $HerokuApp
    heroku apps:destroy --confirm $HerokuApp -a $HerokuApp
    heroku apps
    heroku pipelines

Finally inspect Account Billing and confirm Current Usage after its documented
nightly refresh. Unsubscribe from Eco on the Billing page to prevent the next
monthly $5 renewal. Removal is not instantly reflected in Current Usage, and
already incurred usage is not reversed.

## Local verification record

Verified 2026-09-01 with Docker Desktop 29.2.1:

- The linux/amd64 multi-stage image built successfully.
- The image size was 120,885,201 bytes (about 115.3 MiB).
- Runtime memory after migration, bootstrap, login, one explicit editorial
  approval/publication, and HTTP smoke requests was about 68.1 MiB.
- The container honored PORT=43127.
- Health reported connected; root, SPA fallback, and a committed plant image
  returned 200.
- The first bootstrap created 30 review-ready profiles, 93 source records, and
  122 source links with no revisions. The second created no profile or link and
  retained 30 review-ready profiles with no revisions.
- An authenticated smoke reviewer approved and published one representative
  disposable profile; the public index and article endpoint then exposed it.
- An unauthenticated development-bypass header received 401, an authenticated
  development endpoint received 404, and an unknown API path received 404.

The smoke container and exact disposable database
herbwire_staging_container_verify were removed afterward.

## Cost proof

Checked 2026-09-01 against official Heroku sources.

| Resource | Exact plan identifier | List price | Quantity | Maximum monthly total | Student credits apply | Official source |
|---|---|---:|---:|---:|---|---|
| Eco Dynos subscription; one web process | eco | $5 per 1,000-hour monthly pool | 1 | $5 | Yes | https://devcenter.heroku.com/articles/eco-dyno-hours |
| Heroku Postgres Essential-0 | heroku-postgresql:essential-0 | $5/month maximum | 1 | $5 | Yes | https://devcenter.heroku.com/articles/provisioning-heroku-postgres |
| Total | n/a | n/a | n/a | $10 | Yes | https://www.heroku.com/github-students/ |
| Unused monthly student-credit margin | n/a | n/a | n/a | $3 | n/a | https://www.heroku.com/github-students/ |

The student offer states that $13 of platform credit is available per month and
applies to Heroku Dynos and Heroku Postgres, but not third-party add-ons. Unused
credit does not roll over, and a payment card is charged for excess use. The
current offer page still illustrates its allowance with the deprecated Mini
database name; the current Essential-0 provisioning documentation identifies
the replacement plan and its $5 maximum. This plan uses no metered add-on.
