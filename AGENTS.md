# HerbWire V2 — Repository Instructions

## 1. Source of truth

Before planning or modifying HerbWire, read:

1. `docs/specs/HERBWIRE_SPEC.md`
2. `PLANS.md`
3. Relevant ADRs under `docs/decisions/`
4. The closest applicable `AGENTS.md`

`docs/specs/HERBWIRE_SPEC.md` is the authoritative product and
architecture specification.

If a requested change conflicts with the specification, stop and explain
the conflict. Do not silently diverge. A material architecture change
requires an Architecture Decision Record.

## 2. Project scope

HerbWire V2 is an English-only medicinal-plant encyclopedia and
traditional-medicine discovery platform.

It collects international material from approved sources, preserves
provenance, produces structured English drafts, applies botanical,
evidence, and safety checks, and requires human approval before
publication.

HerbWire does not diagnose, prescribe, provide personalized medical
advice, recommend dosages, or represent traditional use as proven
clinical efficacy.

## 3. Clean-room rule

Do not copy code from the previous HerbWire repository.

The previous frontend may be inspected only for:

- botanical color inspiration;
- visual identity;
- content-card ideas;
- page-composition ideas.

All HerbWire V2 implementation must be clean-room code.

Do not copy NewsFindr code unless a future task explicitly identifies a
small reusable, legally permitted, dependency-compatible component and
human approval is given.

## 4. Current MVP agents

Implement only the essential first workflow:

1. Collector
2. Normalizer and Deduplicator
3. Botanical Enrichment
4. Evidence and Safety
5. Content Composer
6. Editorial QA
7. Publisher

The Pipeline Orchestrator is a platform component.

Postpone Media and Geography, Related Content, advanced multilingual
translation, RAG, vector retrieval, runtime local-LLM generation,
multiple collector integrations, and advanced analytics until an
approved milestone requires them.

Do not create placeholder implementations for postponed agents.

## 5. Architecture rules

Use a modular monolith for the MVP.

Maintain clear boundaries between:

- frontend;
- API;
- database and repositories;
- collectors;
- pipeline orchestration;
- agent/domain logic;
- editorial review;
- publishing.

The frontend must never connect directly to PostgreSQL.

Collectors must never publish content.

The Content Composer must not establish botanical identity or safety
truth.

Only the Publisher may create a public version, and it may do so only
after explicit human approval.

PostgreSQL is the canonical store.

Do not add Redis, MongoDB, Elasticsearch, a vector database,
microservices, Kubernetes, or a message broker without an approved ADR.

## 6. Repository discipline

Do not create a file or directory merely because it may be useful later.

Before adding a file:

1. Identify its owner and responsibility.
2. Identify its required caller or consumer.
3. Confirm that an existing module is not the correct location.
4. Confirm that the current milestone needs it.

Use the repository structure defined in the specification.

Do not invent alternative names or duplicate domain layers.

Avoid catch-all files such as:

- `utils.py`
- `helpers.py`
- `common.py`
- `misc.py`
- `manager.py`

A narrowly named utility module is allowed only when its responsibility
is clear.

No unrelated refactoring during feature tasks.

No dependency may be added without explaining:

- why it is needed;
- why the standard library or an existing dependency is insufficient;
- whether it is actively maintained;
- its license;
- its effect on deployment.

## 7. Planning requirement

For every non-trivial task:

1. Inspect the relevant code and documentation.
2. State the intended outcome.
3. Identify files expected to change.
4. Identify risks and assumptions.
5. Update or create an execution plan in `PLANS.md`.
6. Wait for approval when the task changes architecture or scope.
7. Implement the smallest coherent change.
8. Run relevant verification.
9. Review the final diff.
10. Recommend the best next action.

Do not begin large implementation work from a vague request.

## 8. Desktop-to-CLI handoff

Codex Desktop must recommend CLI execution when the task is better
suited to a terminal, including:

- Git initialization and branch operations;
- worktree creation or removal;
- dependency installation;
- Docker Compose;
- migrations;
- test suites;
- build commands;
- deployment commands;
- authentication;
- long-running development servers;
- commands requiring interactive user input.

Every CLI handoff must provide:

1. Why CLI is preferable.
2. The exact directory.
3. Preconditions.
4. Exact commands, labeled PowerShell or Git Bash.
5. Expected result.
6. What output the user must paste back.
7. A safe stop or recovery command when relevant.
8. A warning if Desktop must not edit the same files concurrently.

Never ask the user to “run the usual command.”

## 9. Worktrees and concurrency

Use one branch and one worktree per independent feature.

Do not use multiple agents on overlapping files.

Before delegating work, identify:

- branch;
- worktree path;
- scope;
- files owned by the task;
- tests required;
- integration method.

Review every delegated diff before merging it.

Do not create a worktree for a tiny sequential edit.

## 10. Data and source rules

Only collect from approved sources in the source registry.

Respect robots policies, rate limits, licenses, attribution requirements,
and source terms.

Preserve:

- source URL;
- canonical URL;
- source name;
- collection timestamp;
- original language;
- original text or permitted extract;
- parser version;
- source publication date;
- claim-to-source relationships.

Never fabricate a source, quotation, botanical name, traditional use,
safety warning, geographic claim, or medical claim.

## 11. Language

Public and editorial output must be English.

International and non-English sources are allowed.

Preserve original-language provenance. Mark translations as
translations. Never silently treat translated text as an original
quotation.

## 12. Safety

Every traditional-use claim must be attributed and qualified.

Potentially dangerous, contraindicated, unsupported, or uncertain
material must be held for human review.

No automatic publication.

No personalized treatment instructions.

No unsupported dosage.

No cure claims.

No model-generated safety fact may be treated as authoritative.

## 13. Secrets and configuration

Never commit:

- API keys;
- passwords;
- database credentials;
- Heroku credentials;
- Zyte credentials;
- tokens;
- private URLs;
- production data.

Use environment variables and maintain `.env.example` with safe
placeholders.

Never print secrets in logs or command output.

## 14. Testing and completion

A task is not complete until:

- acceptance criteria are satisfied;
- relevant tests pass;
- linting and formatting pass;
- migrations are checked when applicable;
- no secret or generated artifact was accidentally added;
- documentation is updated when behavior changed;
- the final diff has been reviewed;
- remaining risks are reported;
- the best next action is recommended.

Never claim a test passed unless it was actually executed.

## 15. Communication

Lead with the result.

Clearly separate:

- verified facts;
- assumptions;
- recommendations;
- blockers.

When blocked, stop and ask instead of inventing missing details.

At the end of every task, report:

1. What changed.
2. What was verified.
3. What was not verified.
4. Risks or follow-up items.
5. The single best next move.