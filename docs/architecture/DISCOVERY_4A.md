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

The current editorial desk exposes bounded generation at **Pipelines**, keeps
detailed persisted history at **Pipeline Runs**, and retains the private queue
at **Discovery Review**. All three require the existing backend editorial
session. The historical bounded PubMed API and CLI remain available.

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

## Unified sequential Discovery generation

The canonical Editorial Desk route is `/admin/pipelines`. Its Discoveries section
reuses official PubMed metadata/normalization, PMID/DOI/URL/content deduplication,
the rich curated article contract, source/event/article/review persistence,
Kew botanical identity and distribution records, and the existing human review
and publication state machine. Candidate identities, study titles, identifiers,
and capacity counts remain server-only until a private draft is persisted.

The finite version-controlled catalogue contains twenty unique PubMed source
packages. Each declares exactly one accepted primary botanical subject, stable
Kew IPNI identifier, source-specific evidence and limitations, conservative
safety context, geography, and a checksum-verified licensed Commons photograph.
A release-ready full ten-item run is accepted only while all ten can be reserved
atomically and at least ten eligible packages remain. `All available` means the
safe surplus above that protected reserve and is capped at ten. An unavailable
request writes nothing and discloses no count or identity.

The strictly sequential order is:

1. Collector Gateway
2. Normalization and Deduplication
3. Relevance and Classification
4. Language, Translation, and Entity Enrichment
5. Botanical Resolver
6. Evidence, Safety, and Provenance
7. Media & Geography Agent
8. Content Composer
9. Editorial QA
10. Private review creation

The last item is a persistence stage, not an autonomous agent. Publisher remains
outside execution. Relevance may begin with an unambiguous scientific name or a
source-present common name only when the separate structured Kew authority record
resolves the exact taxon. Missing provenance, evidence limitations, safety
framing, geography, or photographic licensing holds the candidate. Successful
output remains `needs_review` and unpublished.

Plant automation, Discovery automation, and the retained PubMed runner share the
PostgreSQL partial unique active-run invariant. Each launch commits its run,
items, botanical identity reservations, and lease before returning; a server-side
background task advances stages without polling. On web-process startup, a
supervisor uses row locking and lease ownership to reclaim only queued or expired
Plant/Discovery work. It resets only an interrupted running stage, resumes the
same run, and cannot persist under an obsolete lease. Committed stages, sources,
articles, reviews, media, relationships, and reservations remain idempotent.
Manual retry is retained for genuine terminal failures. No stage approves or
publishes.

Detailed history remains on `/admin/runs`. The Pipelines page uses session storage
only for the current tab's launched run ID: a fresh session has empty result
panels; an active run shows only `Running`; persisted results show only linked
headlines and compact editorial status. No scheduler, second dyno, queue service,
hosted model, runtime download, or TTS is introduced.