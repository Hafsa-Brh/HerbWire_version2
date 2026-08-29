# HerbWire V2 Execution Plans

## Rules

- Only one milestone may be active at a time.
- Every milestone must produce a demonstrable, tested result.
- Do not implement future agents as placeholders.
- Update this file when scope, decisions, blockers, or verification changes.
- Detailed product and architecture requirements live in
  `docs/specs/HERBWIRE_SPEC.md`.

## Current status

Project phase: Governance and repository baseline  
Active milestone: Milestone 0  
Deployment status: Heroku student approval pending  
Zyte status: Student account activated  
Production secrets configured: No  
Application code authorized: Not yet  

## Milestone 0 — Governance and repository baseline

### Goal

Create a clean, controlled Git repository that Codex can safely use
without beginning application implementation.

### Deliverables

- [ ] Git repository initialized
- [ ] `docs/specs/HERBWIRE_SPEC.md`
- [ ] Word specification stored under `docs/reference/`
- [ ] Root `AGENTS.md`
- [ ] Root `PLANS.md`
- [ ] `README.md`
- [ ] `.gitignore`
- [ ] `.env.example`
- [ ] `docs/decisions/ADR-0001-modular-monolith.md`
- [ ] `docs/decisions/ADR-0002-postgresql-system-of-record.md`
- [ ] `docs/decisions/ADR-0003-human-reviewed-publishing.md`
- [ ] Minimal `.codex/config.toml`, using only verified supported settings
- [ ] Baseline committed to Git

### Explicit exclusions

- No frontend scaffolding
- No backend scaffolding
- No dependency installation
- No Docker Compose
- No Zyte spider
- No Heroku deployment
- No database schema
- No application code

### Done when

- Repository structure matches the approved baseline.
- Documentation contains no contradictions.
- Codex reports no missing governance requirement.
- `git status` is clean after the baseline commit.

## Milestone 1 — Deployable walking skeleton

Status: Not started

### Goal

Create the smallest frontend, API, health endpoint, PostgreSQL
connection, migration, tests, and deployment configuration.

### Restrictions

No collection or article generation yet.

## Milestone 2 — First complete editorial vertical slice

Status: Not started

### Goal

Process one fixture record through:

collection → normalization → botanical enrichment → evidence/safety →
draft → editorial review → publication.

The first version should use deterministic fixtures before connecting
Zyte or any live external source.

## Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-08-29 | Start with seven essential logical agents | Provides a complete workflow without unnecessary modules |
| 2026-08-29 | Postpone RAG | No curated corpus or measured retrieval requirement yet |
| 2026-08-29 | Use deterministic fixtures before Zyte | Makes failures reproducible |
| 2026-08-29 | Wait for Heroku approval | Avoid premature provider-specific work |