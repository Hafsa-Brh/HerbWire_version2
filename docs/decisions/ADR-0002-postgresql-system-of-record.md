# Title

ADR-0002: PostgreSQL as the canonical system of record

# Status

Accepted

# Date

2026-08-29

# Context

HerbWire V2 is a provenance-heavy editorial system with relational content, review history, pipeline state, and publication constraints. The specification requires one canonical store and explicitly rejects adding extra databases merely because student offers exist. Database implementation is not part of Milestone 0, but the governance baseline needs the database decision recorded now.

# Decision

PostgreSQL is the canonical system of record for HerbWire V2.

- Database implementation begins in Milestone 1, not Milestone 0.
- PostgreSQL will hold the canonical editorial, provenance, and pipeline state.
- `pgvector` and RAG are not part of the MVP baseline.
- MongoDB or a separate vector database may not be introduced without evidence and a future ADR.

# Consequences

- Data modeling will prioritize relational integrity, explicit constraints, and durable provenance.
- Milestone 1 can proceed with one database strategy instead of evaluating multiple stores.
- Any future retrieval or similarity features must fit this decision unless a later ADR changes it.

# Alternatives considered

- MongoDB as a primary store: rejected because the core problem is relational, review-heavy, and constraint-sensitive.
- Separate vector database during MVP: rejected because RAG is deferred and would add unjustified complexity.
- Database deferral without a recorded choice: rejected because it would invite architecture drift in later milestones.

# Revisit conditions

- A later milestone produces measured evidence that PostgreSQL alone cannot meet a real requirement.
- RAG or similarity features become approved and require a narrowly scoped follow-up decision.

# References

- `docs/specs/HERBWIRE_SPEC.md`
- `AGENTS.md`
- `PLANS.md`
