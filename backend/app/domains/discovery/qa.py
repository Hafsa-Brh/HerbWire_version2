import re

from backend.app.domains.discovery.contracts import (
    DraftContent,
    EvidencePackage,
    QaDecision,
)

PROHIBITED_PATTERNS = (
    r"\bcures?\b",
    r"\bproven treatment\b",
    r"\bsafe and effective\b",
    r"\brecommended dose\b",
    r"\btake\s+\d+\s*(mg|g|ml)\b",
)


def evaluate_draft(draft: DraftContent, evidence: EvidencePackage) -> QaDecision:
    source_linked = bool(evidence.source_record_id) and all(
        evidence.source_record_id in block.get("source_record_ids", [])
        for block in draft.body_blocks
    )
    ambiguous_identity = any(entity["ambiguous"] for entity in evidence.entities)
    combined_text = " ".join(
        [
            draft.headline,
            draft.standfirst,
            *(str(block.get("text", "")) for block in draft.body_blocks),
            *draft.limitations,
            draft.safety_context,
            *draft.cannot_conclude,
        ]
    ).casefold()
    prohibited_language_absent = not any(
        re.search(pattern, combined_text) for pattern in PROHIBITED_PATTERNS
    )
    checklist = {
        "source_linked": source_linked,
        "evidence_excerpt_present": bool(evidence.excerpts),
        "scientific_identity_unambiguous": not ambiguous_identity,
        "limitations_present": bool(draft.limitations),
        "safety_context_present": bool(draft.safety_context.strip()),
        "cannot_conclude_present": bool(draft.cannot_conclude),
        "prohibited_language_absent": prohibited_language_absent,
    }
    reason_codes = tuple(code for code, passed in checklist.items() if not passed)
    return QaDecision(
        passed=all(checklist.values()),
        reason_codes=reason_codes,
        checklist=checklist,
    )
