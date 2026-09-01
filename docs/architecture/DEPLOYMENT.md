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
    deliberately does not approve or publish them. It is the generic workflow
    for a genuinely new editorial corpus, not the initialization path for this
    staging environment.
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

## Distinct corpus workflows

### Generic review-gated bootstrap

The existing bootstrap is retained for a genuinely new editorial corpus. It
imports 30 review-ready profiles, never approves, never publishes, and requires
normal human review. It is never run on web startup or every deployment:

    heroku run python -m backend.app.workers.bootstrap_staging_corpus --confirm-review-required -a $HerokuApp

### One-time reviewed staging transfer

The first HerbWire staging environment must preserve the owner's already
completed review, publication, and revision history. It therefore receives a
one-time transfer from a sanitized disposable clone of the verified local
database. Copying those existing decisions does not create a new approval.
After a successful transfer, never run the generic bootstrap on this staging
database.

The authoritative `herbwire` database itself is not safe for whole-database
`pg:push`: it contains one newsletter subscriber email, one deterministic local
fixture pipeline run with seven stage rows, four unlinked fixture source
records, and one fixture-only source. Those rows must not reach staging. The
source database is read-only throughout; sanitization occurs only in the
disposable `herbwire_staging_transfer` clone.

## Read-only source audit and classification

Audited 2026-09-02 without reading record contents:

- PostgreSQL 17.11; database size 10,188,467 bytes; Alembic
  `20260901_0007`; only the standard `plpgsql` extension.
- `plant_profiles`: 30 required canonical v4 rows, all rich and published.
- `editorial_reviews`: 30 required approved editorial decisions.
- `plant_profile_revisions`: 90 required historical/audit rows. Lavender v3
  and Senna v3 are approved but stale and promotion-ineligible; all 30 v4 rows
  are promoted and the other 58 rows are superseded.
- `plant_profile_sources`: 122 required provenance links.
- `source_records`: 93 required linked records plus four local-only fixture
  records that must be removed from the clone.
- `sources`: five required canonical sources plus one local-only fixture source
  that must be removed from the clone.
- `newsletter_subscriptions`: one private local email; local-only and excluded.
- `pipeline_runs` and `pipeline_stage_results`: one run and seven stage rows
  from the deterministic development fixture; local-only and excluded.
- `alembic_version`: required schema identity.
- No separate harmless-but-optional table or uncertain table was found.
- Count-only scans found no password, API-key, auth-token, session-secret,
  database-URL, localhost, or `127.0.0.1` marker in the retained editorial,
  provenance, source, or pipeline rows.

The source fingerprints are:

- canonical profiles: `0c2c073f21217a873db8e5628fe07d40`
- revision history: `6ceb4c185acf102229e63aa35e527e03`
- editorial reviews: `69f59260e6c548b49f38d0b8749cc8ba`
- canonical source records: `726dfe1469447ece9491c73593dc0f90`
- source links: `2314a9f6c74a2007d864ed8bf2ecad10`

The disposable clone and remote database must reproduce all five fingerprints.
Any mismatch stops the transfer or deployment for owner review.

## Transfer safety and compatibility

Heroku documents [`pg:push`](https://devcenter.heroku.com/articles/managing-heroku-postgres-using-cli#pg-push)
for local-to-Heroku transfers and requires an empty target. Essential-0 is
compatible with the operation. Local PostgreSQL is 17.11, so Phase 2 must
provision the [supported PostgreSQL 17 major](https://devcenter.heroku.com/articles/heroku-postgres-version-support)
explicitly instead of accepting Heroku's current PostgreSQL 18 default. PostgreSQL 17
client tools must be installed on the Windows host and available on `PATH`;
the current Docker image has 17.11 tools, but the current Windows host does not.
The installed Heroku CLI 11.10.0 exposes the required `pg:push` command.

`pg:push` is permitted only for the first initialization of this exact new
staging app. The owner must approve the exact app name, authoritative source
identity (`127.0.0.1:5433/herbwire`), sanitized transfer identity
(`127.0.0.1:5433/herbwire_staging_transfer`), and exclusion set. Record those
non-secret identities before execution. Never run this workflow against
another application, a production database, or a non-empty target.

If the target contains any public table, stop. Do not accept or automate a
`pg:reset` prompt, do not run `pg:reset`, and never use `--confirm` to bypass
target protection.

## Read-only transfer invariants

Run these aggregate queries first against `herbwire`, then against the sanitized
clone, and finally against remote `DATABASE_URL`. They return counts and hashes,
not record contents:

    $InvariantSql = @'
    SELECT count(*) AS canonical_profiles,
           count(*) FILTER (WHERE article_details IS NOT NULL AND article_details <> '{}'::jsonb) AS rich_profiles,
           count(*) FILTER (WHERE article_details IS NULL OR article_details = '{}'::jsonb) AS basic_profiles,
           count(*) FILTER (WHERE status = 'published') AS published_profiles,
           count(*) FILTER (WHERE hero_image->>'kind' = 'licensed_photograph' AND coalesce(hero_image->>'attribution','') <> '' AND coalesce(hero_image->>'checksum_sha256','') <> '') AS licensed_media_profiles,
           count(*) FILTER (WHERE distribution IS NOT NULL AND distribution <> '{}'::jsonb) AS valid_distribution_profiles
      FROM plant_profiles;
    SELECT version, count(*) AS profiles FROM plant_profiles GROUP BY version ORDER BY version;
    SELECT count(*) FILTER (WHERE r.status IN ('needs_review','held')) AS pending_review_revisions,
           count(*) FILTER (WHERE r.status = 'approved' AND r.version > p.version) AS promotion_candidates,
           count(*) FILTER (WHERE r.status = 'approved' AND r.version <= p.version) AS stale_approved_history
      FROM plant_profile_revisions r JOIN plant_profiles p ON p.id = r.plant_profile_id;
    SELECT count(*) AS inconsistent_or_partial_promotions
      FROM plant_profiles p
     WHERE p.status = 'published'
       AND (p.approved_at IS NULL OR p.published_at IS NULL OR p.last_reviewed_at IS NULL
            OR NOT EXISTS (SELECT 1 FROM editorial_reviews er WHERE er.plant_profile_id = p.id AND er.status = 'approved' AND er.decided_at IS NOT NULL));
    SELECT count(*) AS reviews FROM editorial_reviews;
    SELECT status, version, count(*) AS revisions FROM plant_profile_revisions GROUP BY status, version ORDER BY version, status;
    SELECT p.slug, p.version AS canonical_version, r.version AS historical_version, r.status,
           (r.version <= p.version) AS stale_and_ineligible
      FROM plant_profile_revisions r JOIN plant_profiles p ON p.id = r.plant_profile_id
     WHERE p.slug IN ('lavender','senna') AND r.version = 3 ORDER BY p.slug;
    SELECT count(*) AS source_records,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM plant_profile_sources pps WHERE pps.source_record_id = sr.id)) AS linked_source_records,
           count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM plant_profile_sources pps WHERE pps.source_record_id = sr.id)) AS unlinked_source_records
      FROM source_records sr;
    SELECT count(*) AS source_links FROM plant_profile_sources;
    SELECT (SELECT count(*) FROM newsletter_subscriptions) AS newsletter_rows,
           (SELECT count(*) FROM pipeline_runs) AS pipeline_runs,
           (SELECT count(*) FROM pipeline_stage_results) AS pipeline_stages;
    SELECT md5(string_agg(md5(row_to_json(p)::text), '' ORDER BY p.slug)) AS canonical_profile_fingerprint FROM plant_profiles p;
    SELECT md5(string_agg(md5(row_to_json(r)::text), '' ORDER BY r.plant_profile_id::text, r.version)) AS revision_history_fingerprint FROM plant_profile_revisions r;
    SELECT md5(string_agg(md5(row_to_json(er)::text), '' ORDER BY er.plant_profile_id::text, er.id::text)) AS editorial_review_fingerprint FROM editorial_reviews er;
    SELECT md5(string_agg(md5(row_to_json(sr)::text), '' ORDER BY sr.external_identifier)) AS canonical_source_record_fingerprint
      FROM source_records sr WHERE EXISTS (SELECT 1 FROM plant_profile_sources pps WHERE pps.source_record_id = sr.id);
    SELECT md5(string_agg(md5(row_to_json(pps)::text), '' ORDER BY pps.plant_profile_id::text, pps.source_record_id::text, pps.support_role)) AS source_link_fingerprint
      FROM plant_profile_sources pps;
    '@

    $MarkerSql = @'
    SELECT 'plant_profiles' AS table_name, count(*) AS unsafe_marker_rows FROM plant_profiles t WHERE row_to_json(t)::text ~* '(password|api.?key|auth.?token|session.?secret|database.?url|postgres(ql)?://|127[.]0[.]0[.]1|localhost)'
    UNION ALL SELECT 'plant_profile_revisions', count(*) FROM plant_profile_revisions t WHERE row_to_json(t)::text ~* '(password|api.?key|auth.?token|session.?secret|database.?url|postgres(ql)?://|127[.]0[.]0[.]1|localhost)'
    UNION ALL SELECT 'editorial_reviews', count(*) FROM editorial_reviews t WHERE row_to_json(t)::text ~* '(password|api.?key|auth.?token|session.?secret|database.?url|postgres(ql)?://|127[.]0[.]0[.]1|localhost)'
    UNION ALL SELECT 'source_records', count(*) FROM source_records t WHERE row_to_json(t)::text ~* '(password|api.?key|auth.?token|session.?secret|database.?url|postgres(ql)?://|127[.]0[.]0[.]1|localhost)'
    UNION ALL SELECT 'sources', count(*) FROM sources t WHERE row_to_json(t)::text ~* '(password|api.?key|auth.?token|session.?secret|database.?url|postgres(ql)?://|127[.]0[.]0[.]1|localhost)';
    '@

Expected sanitized and remote results: 30 canonical, rich, published, licensed
media, and valid-distribution profiles; zero basic profiles; 30 reviews; 90
revisions; zero pending or promotion-candidate revisions; two stale approved
historical revisions; zero inconsistent promotions; 93 linked and zero
unlinked source records; 122 source links; zero newsletter, pipeline-run, and
pipeline-stage rows; the five exact fingerprints above; and Alembic at the
repository head. Every `$MarkerSql` count must be zero. After deployment, the
public API must also report 30 profiles.

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

The following PowerShell sequence is owner-executed and has not been run. Do
not edit this checkout concurrently.

The corrected order is:

1. Review and merge the readiness branch.
2. Verify the account and active student credit.
3. Verify that no app or pipeline exists.
4. Subscribe to Eco only with explicit owner approval.
5. Create exactly one EU staging app.
6. Select the container stack.
7. Provision exactly one PostgreSQL 17 Essential-0 database.
8. Wait for the database.
9. Verify that the database belongs to the approved app.
10. Verify that its public schema is empty.
11. Verify `127.0.0.1:5433/herbwire` as the authoritative source.
12. Run the final source invariants read-only.
13. Create and verify the sanitized clone, then run the explicitly approved
    one-time `pg:push` from that clone.
14. Remove the temporary password environment variable immediately.
15. Verify remote schema, fingerprints, and Alembic revision.
16. Configure backend-only staging settings and secrets without logging values.
17. Deploy the merged readiness code.
18. Let the release migration confirm head as a no-op.
19. Start exactly one Eco web process.
20. Run remote invariants and HTTP smoke tests.
21. Never run the review-gated bootstrap after a successful transfer.

    Set-Location C:\Users\PC\Documents\ChatGPT\HerbWire_version2
    git switch main
    git pull --ff-only origin main
    git status --short
    $HerokuApp = "<approved-unique-app-name>"

Confirm that the reviewed readiness commits are merged, the account identity
and active student credit are correct, and no app or pipeline exists:

    heroku auth:whoami
    heroku apps
    heroku pipelines

With explicit owner approval, subscribe to Eco on the personal Account Billing
page. Then create exactly one EU app and one PostgreSQL 17 Essential-0 database:

    heroku apps:create $HerokuApp --region eu
    heroku stack:set container -a $HerokuApp
    heroku addons:create heroku-postgresql:essential-0 -a $HerokuApp -- --version=17
    heroku pg:wait -a $HerokuApp

Verify the database belongs to the approved app, is PostgreSQL 17, and has zero
public tables. These commands do not reveal `DATABASE_URL`:

    heroku addons -a $HerokuApp
    heroku pg:info DATABASE_URL -a $HerokuApp
    heroku pg:psql DATABASE_URL -a $HerokuApp --command "SELECT count(*) AS public_table_count FROM pg_catalog.pg_tables WHERE schemaname = 'public';"

The expected count is zero. Any other result stops the procedure. Do not deploy
or run Alembic before the transfer because either action makes the target
non-empty.

Start the existing local PostgreSQL service and record only its non-secret
identity. The expected output is PostgreSQL 17, database `herbwire`, host
`127.0.0.1`, and host port `5433`:

    docker compose up -d postgres
    docker compose port postgres 5432
    docker compose exec -T postgres psql -X -U herbwire -d herbwire -v ON_ERROR_STOP=1 --command "BEGIN TRANSACTION READ ONLY; SELECT current_setting('server_version') AS postgresql_version, current_database() AS database_name; SELECT version_num AS alembic_revision FROM alembic_version; COMMIT;"
    $InvariantSql | docker compose exec -T postgres psql -X -U herbwire -d herbwire -v ON_ERROR_STOP=1
    $MarkerSql | docker compose exec -T postgres psql -X -U herbwire -d herbwire -v ON_ERROR_STOP=1

Review the results against the source baseline above. Verify that the disposable
clone does not already exist; if the result is not zero, stop rather than
dropping or reusing it:

    docker compose exec -T postgres psql -X -U herbwire -d postgres -v ON_ERROR_STOP=1 --command "SELECT count(*) AS existing_transfer_databases FROM pg_database WHERE datname = 'herbwire_staging_transfer';"

After the owner approves the source identity and exclusions, clone the source.
This reads but does not alter `herbwire`; all following writes target only the
disposable clone:

    docker compose exec -T postgres createdb -U herbwire --template=herbwire herbwire_staging_transfer
    docker compose exec -T postgres psql -X -U herbwire -d herbwire_staging_transfer -v ON_ERROR_STOP=1 --command "BEGIN; TRUNCATE newsletter_subscriptions, pipeline_stage_results, pipeline_runs; DELETE FROM source_records sr WHERE NOT EXISTS (SELECT 1 FROM plant_profile_sources pps WHERE pps.source_record_id = sr.id); DELETE FROM sources s WHERE NOT EXISTS (SELECT 1 FROM source_records sr WHERE sr.source_id = s.id); COMMIT;"
    $InvariantSql | docker compose exec -T postgres psql -X -U herbwire -d herbwire_staging_transfer -v ON_ERROR_STOP=1
    $MarkerSql | docker compose exec -T postgres psql -X -U herbwire -d herbwire_staging_transfer -v ON_ERROR_STOP=1

Continue only if the sanitized results and fingerprints match the documented
expectations. The Windows host must also expose PostgreSQL 17 client tools;
the current host does not, so install or expose the official matching client
before Phase 2 and verify:

    Get-Command pg_dump, pg_restore, psql | Select-Object Name,Source
    pg_dump --version
    pg_restore --version

The password-bearing transfer is deliberately interactive. The password is not
placed in command history or echoed. `PGPASSWORD` exists only for the child
operation and is removed in `finally`. The source URL contains no password and
names only the sanitized clone:

    $SecureLocalPgPassword = Read-Host "Local PostgreSQL password" -AsSecureString
    $LocalPgCredential = [pscredential]::new("herbwire", $SecureLocalPgPassword)
    try {
        $env:PGPASSWORD = $LocalPgCredential.GetNetworkCredential().Password
        heroku pg:push "postgresql://herbwire@127.0.0.1:5433/herbwire_staging_transfer" DATABASE_URL --app $HerokuApp
        if ($LASTEXITCODE -ne 0) { throw "pg:push failed; stop for owner review" }
    }
    finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
        $LocalPgCredential = $null
        $SecureLocalPgPassword.Dispose()
        $SecureLocalPgPassword = $null
    }

If `pg:push` offers to reset a target, press Ctrl+C and stop. Never answer the
reset prompt, rerun with `--confirm`, or retry against the now non-empty target.
Record only the approved app name and non-secret source/target identifiers.

Verify the transferred schema and invariants before configuring or deploying:

    heroku pg:info DATABASE_URL -a $HerokuApp
    heroku pg:psql DATABASE_URL -a $HerokuApp --command "SELECT version_num AS alembic_revision FROM alembic_version;"
    heroku pg:psql DATABASE_URL -a $HerokuApp --command $InvariantSql
    heroku pg:psql DATABASE_URL -a $HerokuApp --command $MarkerSql

Set the five non-secret runtime settings and the three backend-only secrets in
the Heroku app Settings page. Do not reveal or copy `DATABASE_URL`, and do not
run an unrestricted `heroku config` command. Required names are
`HERBWIRE_ENVIRONMENT`, `HERBWIRE_FRONTEND_ORIGIN`,
`HERBWIRE_SESSION_COOKIE_NAME`, `HERBWIRE_SESSION_COOKIE_SECURE`,
`HERBWIRE_ENABLE_DEVELOPMENT_ENDPOINTS`, `HERBWIRE_ADMIN_EMAIL`,
`HERBWIRE_ADMIN_PASSWORD`, and `HERBWIRE_SESSION_SECRET`.

Deploy only after the transfer and configuration checks:

    heroku git:remote -a $HerokuApp
    git push heroku HEAD:main
    heroku ps:type web=eco -a $HerokuApp
    heroku ps:scale web=1 -a $HerokuApp
    heroku ps -a $HerokuApp
    heroku addons -a $HerokuApp
    heroku releases -a $HerokuApp
    heroku pg:psql DATABASE_URL -a $HerokuApp --command $InvariantSql
    heroku pg:psql DATABASE_URL -a $HerokuApp --command $MarkerSql
    $Health = Invoke-RestMethod "https://$HerokuApp.herokuapp.com/api/v1/health"
    $Plants = Invoke-RestMethod "https://$HerokuApp.herokuapp.com/api/v1/plants?page=1&page_size=100"
    $Health
    $Plants.total

The release migration must be a no-op at repository head. Expected result: one
Eco web process, one PostgreSQL 17 Essential-0 database, connected health, and
30 public profiles with the transferred editorial history intact. Do not run
`bootstrap_staging_corpus` after a successful transfer.

Paste back only command status, plan/version names, aggregate counts,
fingerprints, and HTTP status/results. Never paste configuration output,
credentials, subscriber data, or record contents.

If the release fails, scale web to zero and inspect release/application logs:

    heroku ps:scale web=0 -a $HerokuApp
    heroku releases:output -a $HerokuApp
    heroku logs --tail -a $HerokuApp

If transfer verification fails, do not deploy, reset, or retry. Stop for owner
review. Retain the disposable clone until remote verification succeeds; remove
it later only with explicit approval naming `herbwire_staging_transfer`.

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
