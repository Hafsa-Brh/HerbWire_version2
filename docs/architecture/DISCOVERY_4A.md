# Milestone 4A: PubMed discovery review slice

Milestone 4A implements one specification-aligned PubMed discovery path from
collection through a review-ready editorial draft. It intentionally does not
complete scheduling, automatic publication, multi-source collection, Zyte
integration, RAG, TTS or the full agent architecture required by the complete
Milestone 4.

## Source and request boundary

The only live provider is the official NCBI E-utilities API. The collector uses
ESearch to obtain a bounded PMID list and EFetch to retrieve PubMed XML records.
It follows the NCBI E-utilities usage guidance and parameter reference:

- <https://www.ncbi.nlm.nih.gov/books/NBK25497/>
- <https://www.ncbi.nlm.nih.gov/books/NBK25499/>

The fixed query covers medicinal plants, phytotherapy, herbal medicine, and
ethnopharmacology, restricted to English. The mindate, maxdate, and
datetype=pdat parameters carry the exact caller-supplied publication window.
The server accepts at most five records and a window of at most 31 days.
Requests identify HerbWire with tool and a backend-only contact email, use a
timeout, remain below the unauthenticated rate limit, and retry only bounded
transient failures. Retry-After is honored with a finite cap.

Set these backend-only configuration names for an explicitly approved live run:

- HERBWIRE_NCBI_EMAIL
- HERBWIRE_NCBI_REQUEST_TIMEOUT_SECONDS
- HERBWIRE_NCBI_MAX_RETRIES

Values must remain outside source control and browser bundles. Saved XML
fixtures are the default verification path and make no network request.

## Pipeline and state

One in-process orchestrator owns the transaction and stage record boundaries:

1. collect
2. normalize
3. deduplicate
4. detect_relevance
5. enrich_evidence
6. draft_article
7. qa_policy_gate
8. queue_editorial_review

Runs persist status, UTC timestamps, safe failure codes, attempts, counts, and
bounded record references. Source records are deduplicated by PMID first, then
normalized DOI, canonical URL, and normalized-content hash. PostgreSQL unique
constraints are the final race-condition boundary.

Relevance requires a recognizable medicinal plant relationship. Explicit
exclusions include acupuncture-only, yoga, massage, meditation, generic
complementary medicine without a plant relationship, conventional-drug-only
work, agriculture, ornamental plants, cosmetic marketing, and advertisements.
A common-name-only match is marked ambiguous and fails closed at QA.

The deterministic enrichment and writing implementations consume only
source-supported metadata and bounded abstract excerpts. They preserve evidence
locations, limitations, safety context, and statements about what cannot be
concluded. Their protocols are replaceable by later approved providers without
changing collection or editorial storage.

A passing draft becomes needs_review; an incomplete or unsupported draft is
held. An authenticated editor may approve, hold, or reject. Milestone 4A has no
discovery publication endpoint, and public discovery APIs select only published
rows. Approved drafts therefore remain private for a later
specification-aligned Publisher increment.

## Execution

The editorial desk exposes a bounded manual trigger at **Pipeline Runs** and a
private queue at **Discovery Review**. Both require the existing backend
editorial session.

The CLI calls the same orchestrator. Fixture execution is explicit and offline:

~~~powershell
python -m backend.app.workers.run_pubmed_discovery --start-date 2026-08-01 --end-date 2026-09-01 --max-records 1 --fixture-directory backend/tests/fixtures/pubmed
~~~

Live execution requires both an owner-approved window and the explicit --live
flag. It must use a disposable or approved operational database, never the
canonical local development database for testing:

~~~powershell
python -m backend.app.workers.run_pubmed_discovery --start-date YYYY-MM-DD --end-date YYYY-MM-DD --max-records 5 --live
~~~

No scheduler, worker process, bootstrap, or web-startup hook invokes this
pipeline. Repeating the same provider/window/limit returns the persisted run;
reprocessing the same PubMed material under another window reuses its source,
event, draft, and review identities.