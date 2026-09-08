"""Canonical cross-domain botanical subject eligibility."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Iterable

from backend.app.models.encyclopedia import (
    DiscoveryArticlePlant,
    DiscoveryEvent,
    DiscoveryPipelineItem,
    PipelineBotanicalReservation,
    PipelineRun,
    PlantPipelineItem,
    PlantProfile,
    PlantProfileRevision,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_UNAVAILABLE = (
    "The requested batch is temporarily unavailable while the protected "
    "editorial reserve is maintained."
)


def normalize_identity(value: str) -> str:
    """Normalize case, Unicode, punctuation, and whitespace for identity matching."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_like = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return _NON_ALNUM.sub("", ascii_like.casefold())


def _keys(kind: str, values: Iterable[str | None]) -> set[str]:
    return {
        f"{kind}:{normalized}"
        for value in values
        if value and (normalized := normalize_identity(value))
    }


@dataclass(frozen=True)
class BotanicalSubject:
    taxon_identifier: str
    accepted_scientific_name: str
    botanical_author: str = ""
    synonyms: tuple[str, ...] = ()
    common_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason_code: str | None = None
    reason: str | None = None
    matched_key: str | None = None


def subject_identity_keys(subject: BotanicalSubject) -> set[str]:
    scientific_names = [subject.accepted_scientific_name, *subject.synonyms]
    return (
        _keys("taxon", [subject.taxon_identifier])
        | _keys("scientific", scientific_names)
        | _keys("common", subject.common_names)
    )


def candidate_identity_keys(candidate) -> set[str]:
    """Backward-compatible Plant catalogue identity helper."""
    return subject_identity_keys(subject_from_plant_candidate(candidate))


def subject_from_plant_candidate(candidate) -> BotanicalSubject:
    return BotanicalSubject(
        taxon_identifier=candidate.taxon_identifier,
        accepted_scientific_name=candidate.accepted_scientific_name,
        botanical_author=candidate.botanical_author,
        synonyms=tuple(candidate.synonyms),
        common_names=tuple(candidate.common_names),
    )


def subject_from_discovery_candidate(candidate) -> BotanicalSubject:
    subject = candidate.primary_botanical_subject
    return BotanicalSubject(
        taxon_identifier=subject.taxon_identifier,
        accepted_scientific_name=subject.accepted_scientific_name,
        botanical_author=subject.botanical_author,
        synonyms=tuple(subject.synonyms),
        common_names=tuple(subject.common_names),
    )


def _profile_subject(profile: PlantProfile) -> BotanicalSubject:
    return BotanicalSubject(
        taxon_identifier=profile.taxon_identifier,
        accepted_scientific_name=profile.accepted_scientific_name,
        botanical_author=profile.botanical_author,
        synonyms=tuple(profile.known_synonyms),
        common_names=(profile.display_common_name,),
    )


def _revision_subject(revision: PlantProfileRevision) -> BotanicalSubject:
    profile = revision.content_payload.get("profile", {})
    return BotanicalSubject(
        taxon_identifier=str(profile.get("taxon_identifier") or ""),
        accepted_scientific_name=str(profile.get("accepted_scientific_name") or ""),
        botanical_author=str(profile.get("botanical_author") or ""),
        synonyms=tuple(profile.get("known_synonyms") or ()),
        common_names=tuple(
            value
            for value in (profile.get("display_common_name"),)
            if isinstance(value, str)
        ),
    )


def _event_subject(event: DiscoveryEvent) -> BotanicalSubject | None:
    identity = event.evidence_package.get("botanical_identity") or {}
    if not isinstance(identity, dict):
        return None
    scientific = identity.get("accepted_scientific_name")
    taxon = identity.get("taxon_identifier") or identity.get("authority_taxon_id")
    if not scientific or not taxon:
        return None
    common_names = identity.get("common_names") or [identity.get("common_name")]
    return BotanicalSubject(
        taxon_identifier=str(taxon),
        accepted_scientific_name=str(scientific),
        botanical_author=str(identity.get("botanical_author") or ""),
        synonyms=tuple(identity.get("synonyms") or ()),
        common_names=tuple(
            value for value in common_names if isinstance(value, str) and value
        ),
    )


def _snapshot_subject(snapshot: dict) -> BotanicalSubject | None:
    nested = snapshot.get("primary_botanical_subject")
    value = nested if isinstance(nested, dict) else snapshot
    scientific = value.get("accepted_scientific_name")
    taxon = value.get("taxon_identifier") or value.get("authority_taxon_id")
    if not scientific or not taxon:
        return None
    common_names = value.get("common_names") or [value.get("common_name")]
    return BotanicalSubject(
        taxon_identifier=str(taxon),
        accepted_scientific_name=str(scientific),
        botanical_author=str(value.get("botanical_author") or ""),
        synonyms=tuple(value.get("synonyms") or ()),
        common_names=tuple(
            item for item in common_names if isinstance(item, str) and item
        ),
    )


def existing_identity_keys(
    session: Session, *, exclude_run_id: uuid.UUID | None = None
) -> set[str]:
    """Return only structured botanical identities; article prose is never searched."""
    keys: set[str] = set()
    for profile in session.scalars(select(PlantProfile)).all():
        keys.update(subject_identity_keys(_profile_subject(profile)))
    for revision in session.scalars(select(PlantProfileRevision)).all():
        keys.update(subject_identity_keys(_revision_subject(revision)))
    for event in session.scalars(select(DiscoveryEvent)).all():
        if subject := _event_subject(event):
            keys.update(subject_identity_keys(subject))
    for relationship in session.scalars(select(DiscoveryArticlePlant)).all():
        profile = session.get(PlantProfile, relationship.plant_profile_id)
        if profile is not None:
            keys.update(subject_identity_keys(_profile_subject(profile)))

    reservation_query = select(PipelineBotanicalReservation.identity_key)
    if exclude_run_id is not None:
        reservation_query = reservation_query.where(
            PipelineBotanicalReservation.pipeline_run_id != exclude_run_id
        )
    keys.update(session.scalars(reservation_query).all())

    for model in (PlantPipelineItem, DiscoveryPipelineItem):
        query = select(model)
        if exclude_run_id is not None:
            query = query.where(model.pipeline_run_id != exclude_run_id)
        for item in session.scalars(query).all():
            if subject := _snapshot_subject(item.candidate_snapshot):
                keys.update(subject_identity_keys(subject))
    return keys


def check_subject_eligibility(
    session: Session,
    subject: BotanicalSubject,
    *,
    exclude_run_id: uuid.UUID | None = None,
    batch_keys: set[str] | None = None,
) -> EligibilityResult:
    candidate_keys = subject_identity_keys(subject)
    if not candidate_keys:
        return EligibilityResult(
            False,
            "missing_botanical_identity",
            "A stable structured botanical identity is required.",
        )
    if batch_keys is not None and candidate_keys & batch_keys:
        key = sorted(candidate_keys & batch_keys)[0]
        return EligibilityResult(
            False,
            "duplicate_within_batch",
            "The candidate duplicates another botanical subject selected in this run.",
            key,
        )
    matched = candidate_keys & existing_identity_keys(
        session, exclude_run_id=exclude_run_id
    )
    if matched:
        key = sorted(matched)[0]
        return EligibilityResult(
            False,
            "represented_botanical_subject",
            "This botanical subject is already represented or reserved.",
            key,
        )
    return EligibilityResult(True)


def check_candidate_eligibility(
    session: Session,
    candidate,
    *,
    exclude_run_id: uuid.UUID | None = None,
    batch_keys: set[str] | None = None,
) -> EligibilityResult:
    return check_subject_eligibility(
        session,
        subject_from_plant_candidate(candidate),
        exclude_run_id=exclude_run_id,
        batch_keys=batch_keys,
    )


def reserve_subject(
    session: Session,
    *,
    run_id: uuid.UUID,
    domain: str,
    candidate_key: str,
    subject: BotanicalSubject,
) -> None:
    for identity_key in sorted(subject_identity_keys(subject)):
        session.add(
            PipelineBotanicalReservation(
                pipeline_run_id=run_id,
                domain=domain,
                candidate_key=candidate_key,
                identity_key=identity_key,
            )
        )


def protected_reserve_message() -> str:
    return _UNAVAILABLE


def active_pipeline_domain(session: Session) -> str | None:
    run = session.scalar(
        select(PipelineRun)
        .where(
            PipelineRun.status == "running",
            PipelineRun.pipeline_type.in_(
                (
                    "plant_profile_automation",
                    "discovery_article_automation",
                    "pubmed_discovery_review",
                )
            ),
        )
        .order_by(PipelineRun.started_at)
        .limit(1)
    )
    if run is None:
        return None
    return {
        "plant_profile_automation": "plants",
        "discovery_article_automation": "discoveries",
        "pubmed_discovery_review": "pubmed",
    }[run.pipeline_type]
