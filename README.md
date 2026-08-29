# HerbWire V2

HerbWire V2 is an English-only medicinal-plant encyclopedia and traditional-medicine discovery platform. It is intended to collect international source material, preserve provenance, produce structured English drafts, apply botanical, evidence, and safety checks, and require explicit human approval before any public publication.

HerbWire does not diagnose, prescribe, recommend personalized treatment, provide dosage guidance, or present traditional use as proven clinical efficacy.

## Current status

This repository is in the Milestone 0 governance baseline stage.

- No application code has been implemented yet.
- No frontend, backend, database schema, collectors, tests, or deployment configuration are active.
- No deployment is active.
- Heroku approval is still pending, and no Heroku resource should be created yet.
- A Zyte student account is available, but Zyte is not integrated into this repository.

## MVP logical agents

The initial MVP is limited to seven essential logical agents:

1. Collector
2. Normalizer and Deduplicator
3. Botanical Enrichment
4. Evidence and Safety
5. Content Composer
6. Editorial QA
7. Publisher

The Pipeline Orchestrator is a platform component rather than a content-generating agent.

## Scope

- Product output is English-only.
- Source discovery is international and may include non-English source material.
- The editorial focus is medicinal plants and traditional medicine.
- Safety, provenance, and human review are mandatory parts of the design.

## Planned milestone sequence

1. Milestone 0: Governance and repository baseline
2. Milestone 1: Deployable walking skeleton
3. Milestone 2: First complete editorial vertical slice

Future milestones are described in the authoritative specification and may be refined only through approved documentation updates.

## Authoritative documents

- `docs/specs/HERBWIRE_SPEC.md`
- `PLANS.md`
- `AGENTS.md`
- `docs/decisions/`
- `docs/reference/HerbWire_V2_Functional_Technical_Specification_v1.0.docx`

## Current repository tree

```text
HerbWire_version2/
├── .codex/
│   └── config.toml
├── .github/
│   └── pull_request_template.md
├── docs/
│   ├── decisions/
│   │   ├── ADR-0001-modular-monolith.md
│   │   ├── ADR-0002-postgresql-system-of-record.md
│   │   └── ADR-0003-human-reviewed-publishing.md
│   ├── reference/
│   │   └── HerbWire_V2_Functional_Technical_Specification_v1.0.docx
│   └── specs/
│       └── HERBWIRE_SPEC.md
├── .env.example
├── .gitignore
├── AGENTS.md
├── PLANS.md
└── README.md
```

## Operational note

This repository intentionally does not claim installation, bootstrap, run, test, Docker, database, collector, or deployment commands yet. Those commands should be added only when the corresponding implementation exists and has been verified.
