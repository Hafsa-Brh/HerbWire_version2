# Encyclopedia Corpus Operations

## Ownership and format

The curated corpus lives in `backend/app/domains/encyclopedia/corpus.json`. Its schema and cross-record validation live in `backend/app/domains/encyclopedia/corpus.py`. PostgreSQL is the system of record after import; the JSON file is a deterministic, reviewable input, not a frontend fixture.

Each profile has a stable slug and accepted scientific name, article fields, taxonomy identifiers, qualified safety and evidence wording, source links, licensed media metadata, structured distribution entries, and editorial readiness. The importer orders records deterministically and rejects duplicate slugs, accepted names, source URLs, and media checksums.

## Source policy

- Taxonomy and distribution use an inspected POWO/WCVP taxon page and retain its exact URL and identifier.
- Traditional-use, evidence, and safety statements use inspected official NCCIH or EMA material. Claims are paraphrased and qualified; source text is not copied into the corpus.
- Each major article responsibility must be covered by the source records linked to that profile.
- URLs, title, publisher, source type, access date, covered sections, citation text, and provenance notes are required.
- An inaccessible or ambiguous source is not evidence. Hold the profile until a suitable authoritative source is available.

## Image policy

Public profile media is stored under `frontend/public/media/plants/`; image binaries are not stored in PostgreSQL and are not hotlinked. Every record must include the exact Commons source page, original URL, creator, explicit reuse license, license URL, attribution, download date, MIME type, dimensions, SHA-256 checksum, alt text, and caption.

Reject unclear rights, all-rights-reserved media, search-result URLs, low-resolution thumbnails, and images whose identity cannot be tied to the accepted taxon. A missing licensed image is an honest fallback and blocks `ready_for_review` status.

## Distribution methodology

HerbWire stores status-bearing distribution entries (`native`, `introduced`, or `unknown`) and always renders accessible textual lists. The corpus uses sourced summaries and links to POWO for the maintained WCVP WGSRPD Level 3 list.

HerbWire does not copy or screenshot POWO's rendered map. WCVP distribution records are retrieved through the GBIF-hosted WCVP dataset (CC BY 4.0, DOI `10.15468/6h8ucr`). Their TDWG Level 3 codes are mapped to ISO countries using the official WGSRPD Edition 2 Level 3/4 cross-reference tables. All profiles carry reviewed `map_countries` metadata and render a responsive country-level overview using the separately licensed `@svg-maps/world` boundary package (CC BY 4.0). Native, introduced, overlapping, and uncertain-origin statuses are distinguished in an accessible legend, and the map is loaded only on article pages.

The country visualization is an aggregation of botanical regions, not an assertion that a subnational WGSRPD region covers an entire country uniformly. The sourced textual regions remain authoritative. Exact WGSRPD polygon rendering is intentionally omitted because the available converted geometry does not carry a sufficiently clear independent reuse license.

## Editorial readiness

A profile can be ready for review only when accepted taxonomy, required article sections, qualified traditional-use language, safety cautions, evidence limitations, sources, licensed local media, and sourced distribution are present. Import never approves or publishes a profile. New profiles enter `needs_review`; existing approval and publication state is preserved.

The backend publication gate independently requires an approved review and rechecks source, safety, evidence, media, attribution, checksum, and distribution completeness.

## Import and verification

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus --validate-only
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus --batch A
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus --batch B
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus --batch C
.\.venv\Scripts\python.exe -m scripts.import_encyclopedia_corpus
```

The final command is the idempotency check: it should report zero created or updated profiles and zero new links when the database already matches the manifest. Destructive migration testing is permitted only against the exact database name `herbwire_m2_migration_verify`.

## Adding the 31st plant

1. Verify the accepted taxon and exact identifier on POWO/IPNI.
2. Inspect authoritative traditional-use and safety/evidence sources.
3. Select an exact-species image with explicit compatible reuse rights and download a deterministic derivative.
4. Record the checksum, dimensions, creator, attribution, and license.
5. Add sourced native/introduced distribution entries or mark unavailable honestly.
6. Add one schema-valid profile and unique source records to `corpus.json`.
7. Run validation, focused corpus tests, and a disposable-database import twice before importing to the main local database.
8. Confirm the new profile remains `needs_review` and is absent from public APIs until a human approves and publishes it through the editorial desk.
