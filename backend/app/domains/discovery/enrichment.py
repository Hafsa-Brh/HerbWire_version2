import re

from backend.app.domains.discovery.contracts import (
    EvidencePackage,
    NormalizedDiscoveryRecord,
    RelevanceDecision,
)


class DeterministicEvidenceEnricher:
    name = "deterministic-evidence-v1"

    def enrich(
        self,
        record: NormalizedDiscoveryRecord,
        source_record_id: str,
        decision: RelevanceDecision,
    ) -> EvidencePackage:
        excerpts: list[dict] = []
        sentences = re.split(r"(?<=[.!?])\s+", record.abstract or "")
        labels = [str(entity["label"]).casefold() for entity in decision.entities]
        for index, sentence in enumerate(sentences):
            normalized = " ".join(sentence.split())
            if not normalized or not any(
                label in normalized.casefold() for label in labels
            ):
                continue
            excerpts.append(
                {
                    "source_record_id": source_record_id,
                    "location": f"abstract_sentence:{index + 1}",
                    "text": normalized[:300],
                    "truncated": len(normalized) > 300,
                }
            )
            if len(excerpts) == 2:
                break

        publication_types = [
            str(value).casefold()
            for value in record.metadata.get("publication_types", [])
        ]
        joined_types = " ".join(publication_types)
        if (
            "randomized controlled trial" in joined_types
            or "clinical trial" in joined_types
        ):
            evidence_type = "clinical research"
        elif "review" in joined_types or "meta-analysis" in joined_types:
            evidence_type = "review/synthesis"
        elif any(
            term in (record.abstract or "").casefold()
            for term in ("in vitro", "animal model", "mice", "rats")
        ):
            evidence_type = "laboratory/preclinical research"
        else:
            evidence_type = "insufficient/unclear"

        limitations = [
            "The deterministic pipeline uses PubMed metadata and the bounded "
            "indexed abstract, not the full paper."
        ]
        if not record.abstract:
            limitations.append("No abstract was available from PubMed.")
        if any(entity["ambiguous"] for entity in decision.entities):
            limitations.append(
                "At least one common plant name lacks source-supported "
                "scientific-name resolution."
            )
        return EvidencePackage(
            source_record_id=source_record_id,
            source_identifiers={
                "pmid": record.external_identifier,
                "doi": record.doi,
                "canonical_url": record.canonical_url,
            },
            category=decision.category,
            language=record.original_language,
            evidence_type=evidence_type,
            entities=decision.entities,
            excerpts=tuple(excerpts),
            limitations=tuple(limitations),
        )
