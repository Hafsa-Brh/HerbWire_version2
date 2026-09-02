import re
from dataclasses import dataclass

from backend.app.domains.discovery.contracts import (
    NormalizedDiscoveryRecord,
    RelevanceDecision,
)

REJECT_RULES = {
    "acupuncture_only": ("acupuncture",),
    "yoga_only": (" yoga ",),
    "massage_only": ("massage",),
    "meditation_only": ("meditation",),
    "agriculture_only": ("agricultur", "crop yield"),
    "ornamental_only": ("ornamental plant",),
    "cosmetic_marketing": ("cosmetic marketing", "beauty product"),
    "advertisement": ("advertisement", "sponsored product"),
}


@dataclass(frozen=True)
class PlantTerm:
    common_name: str
    scientific_name: str


def _contains(haystack: str, needle: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(needle.casefold())}(?!\w)", haystack))


def _category(haystack: str) -> str:
    if any(
        term in haystack for term in ("adverse", "toxicity", "safety", "interaction")
    ):
        return "research_discovery_safety"
    if any(term in haystack for term in ("randomized", "clinical trial", "patient")):
        return "research_discovery_clinical"
    if any(term in haystack for term in ("taxonomy", "authentication", "adulteration")):
        return "authentication"
    if any(term in haystack for term in ("traditional use", "ethnopharmacolog")):
        return "tradition_heritage"
    return "research_discovery_pharmacology"


def detect_relevance(
    record: NormalizedDiscoveryRecord, plant_terms: list[PlantTerm]
) -> RelevanceDecision:
    haystack = f" {record.title} {record.abstract or ''} ".casefold()
    rejected = [
        code
        for code, terms in REJECT_RULES.items()
        if any(term in haystack for term in terms)
    ]
    if rejected:
        return RelevanceDecision(
            relevant=False,
            category="irrelevant",
            confidence=1.0,
            reasons=tuple(rejected),
            evidence_signals=(),
            entities=(),
        )

    entities: list[dict] = []
    signals: list[str] = []
    for plant in plant_terms:
        scientific_match = " ".join(plant.scientific_name.split()[:2])
        scientific_present = _contains(haystack, scientific_match)
        common_present = _contains(haystack, plant.common_name)
        if not scientific_present and not common_present:
            continue
        entities.append(
            {
                "type": "medicinal_plant",
                "label": scientific_match if scientific_present else plant.common_name,
                "common_name": plant.common_name,
                "scientific_name": scientific_match if scientific_present else None,
                "scientific_name_supported_by_source": scientific_present,
                "ambiguous": not scientific_present,
            }
        )
        signals.append(
            f"scientific_name:{scientific_match}"
            if scientific_present
            else f"common_name:{plant.common_name}"
        )

    if not entities:
        return RelevanceDecision(
            relevant=False,
            category="insufficient",
            confidence=0.95,
            reasons=("no_identifiable_medicinal_plant",),
            evidence_signals=(),
            entities=(),
        )

    ambiguous = any(entity["ambiguous"] for entity in entities)
    return RelevanceDecision(
        relevant=True,
        category=_category(haystack),
        confidence=0.7 if ambiguous else 0.98,
        reasons=(
            "medicinal_plant_common_name_requires_review"
            if ambiguous
            else "supported_scientific_plant_name",
        ),
        evidence_signals=tuple(signals),
        entities=tuple(entities),
    )
