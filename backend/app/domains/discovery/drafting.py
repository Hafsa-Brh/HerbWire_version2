from backend.app.domains.discovery.contracts import (
    DiscoveryDraftWriter,
    DraftContent,
    EvidencePackage,
    NormalizedDiscoveryRecord,
)


class DeterministicDiscoveryDraftWriter(DiscoveryDraftWriter):
    name = "deterministic-discovery-draft-v1"

    def write(
        self, record: NormalizedDiscoveryRecord, evidence: EvidencePackage
    ) -> DraftContent:
        plant_labels = ", ".join(str(entity["label"]) for entity in evidence.entities)
        journal_context = f" in {record.journal}" if record.journal else ""
        publication_context = (
            f" dated {record.publication_date}" if record.publication_date else ""
        )
        return DraftContent(
            slug=f"pubmed-{record.external_identifier}",
            headline=record.title,
            standfirst=(
                f"A PubMed-indexed {evidence.evidence_type} record concerning "
                f"{plant_labels} has entered HerbWire's human editorial review."
            ),
            body_blocks=(
                {
                    "heading": "What the source reports",
                    "text": (
                        f"PubMed indexes this English-language record{journal_context}"
                        f"{publication_context}. Its title and abstract identify "
                        f"{plant_labels} as central to the reported work."
                    ),
                    "source_record_ids": [evidence.source_record_id],
                },
                {
                    "heading": "Evidence context",
                    "text": (
                        f"The source is classified for editorial purposes as "
                        f"{evidence.evidence_type}. This label describes the indexed "
                        "record and is not a verdict about clinical efficacy."
                    ),
                    "source_record_ids": [evidence.source_record_id],
                },
                {
                    "heading": "Why editorial review is required",
                    "text": (
                        "An editor must inspect the linked source, verify botanical "
                        "identity and study design, and decide whether any reported "
                        "finding can be summarized without overstating the evidence."
                    ),
                    "source_record_ids": [evidence.source_record_id],
                },
            ),
            limitations=evidence.limitations
            + (
                "The pipeline has not independently assessed the full methods, "
                "results, statistical analysis, or conflicts of interest.",
            ),
            safety_context=(
                "This review draft does not establish that a preparation is safe, "
                "effective, or appropriate for any person. Safety and interaction "
                "claims require separate source-supported editorial review."
            ),
            cannot_conclude=(
                "No treatment recommendation can be made from this draft.",
                "No dosage or preparation instruction can be inferred.",
                "No causal or clinical efficacy claim is established by "
                "indexing alone.",
            ),
        )
