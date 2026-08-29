# Title

ADR-0003: Human-reviewed publishing is mandatory

# Status

Accepted

# Date

2026-08-29

# Context

HerbWire V2 handles medicinal-plant and traditional-medicine content where inaccurate, overstated, or unsafe claims could create real harm. The specification requires human approval before publication and separates collection, composition, review, and publishing responsibilities. Milestone 0 needs this governance baseline established before any application implementation begins.

# Decision

No public HerbWire content may be published without explicit human editorial approval.

- Collectors and composers cannot publish content.
- The Publisher may accept only approved immutable content versions.
- Safety or evidence holds cannot be bypassed automatically.
- Traditional use must not be represented as proven clinical efficacy.
- Automated systems may prepare drafts and review packets, but they do not grant publication authority.

# Consequences

- Publication workflows must include an explicit human review and approval step.
- System boundaries must prevent collectors, enrichment modules, or draft composers from publishing directly.
- Auditability and approval records become first-class requirements for later milestones.
- Some throughput is intentionally traded for safety and editorial control.

# Alternatives considered

- Automatic publication after deterministic checks: rejected because passing checks is not equivalent to human editorial approval.
- Collector-owned publication: rejected because collection and publication must remain separated.
- Model-led approval: rejected because automated systems cannot be treated as authoritative for safety-sensitive publication.

# Revisit conditions

- Governance or product scope changes require a different publication authority model.
- A later milestone proposes a narrower automation path and can prove it preserves explicit human approval.

# References

- `docs/specs/HERBWIRE_SPEC.md`
- `AGENTS.md`
- `PLANS.md`
