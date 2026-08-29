# Title

ADR-0001: Modular monolith for the HerbWire V2 MVP

# Status

Accepted

# Date

2026-08-29

# Context

HerbWire V2 needs a delivery approach that preserves clear boundaries between frontend, API, database, collectors, pipeline orchestration, editorial logic, and publishing without introducing premature operational complexity. The authoritative specification requires a modular monolith for the MVP and explicitly avoids distributed infrastructure unless a later decision proves it necessary.

# Decision

HerbWire V2 will use a modular monolith for the MVP.

- Logical agent boundaries are implemented as modules with explicit contracts inside one codebase.
- These logical agents are not independent microservices.
- The system must preserve clear ownership boundaries between collection, normalization, enrichment, editorial review, and publishing.
- Redis, a message broker, Kubernetes, or other distributed platform additions are not allowed without a future ADR that demonstrates clear need.

# Consequences

- Development remains simpler to reason about during the baseline and early implementation milestones.
- Repository structure and contracts must enforce boundaries that could support later extraction if justified.
- Operational overhead is reduced compared with a distributed system.
- A future extraction of any module into a separate service would require an explicit architecture review and ADR.

# Alternatives considered

- Microservices from the start: rejected because the MVP does not yet justify the deployment, tracing, queueing, and coordination overhead.
- Single undifferentiated application layer: rejected because it would blur responsibilities and increase architecture drift.

# Revisit conditions

- Measured concurrency, deployment, or team-scaling constraints show the modular monolith is no longer adequate.
- A future milestone proves that one bounded module needs independent scaling or isolation.

# References

- `docs/specs/HERBWIRE_SPEC.md`
- `AGENTS.md`
- `PLANS.md`
