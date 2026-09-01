"""Explicit, idempotent bootstrap for a fresh staging database."""

import argparse
import json

from backend.app.core.settings import get_settings
from backend.app.db.session import get_session_factory
from backend.app.domains.encyclopedia.corpus import load_corpus
from backend.app.domains.encyclopedia.service import seed_curated_profiles
from backend.app.models.encyclopedia import PlantProfile, PlantProfileRevision
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

EXPECTED_PROFILE_COUNT = 30


def bootstrap_staging_corpus(session: Session) -> dict[str, int]:
    manifest = load_corpus()
    slugs = {profile.slug for profile in manifest.profiles}
    if len(slugs) != EXPECTED_PROFILE_COUNT:
        raise ValueError("staging bootstrap requires exactly 30 corpus profiles")

    result = seed_curated_profiles(session)
    pending_revisions = session.scalar(
        select(func.count())
        .select_from(PlantProfileRevision)
        .where(
            PlantProfileRevision.plant_profile.has(PlantProfile.slug.in_(slugs)),
            PlantProfileRevision.status.in_({"needs_review", "approved", "held"}),
        )
    )
    if pending_revisions:
        raise ValueError("staging bootstrap refuses pending canonical revisions")

    profiles = list(
        session.scalars(
            select(PlantProfile)
            .where(PlantProfile.slug.in_(slugs))
            .options(selectinload(PlantProfile.sources))
        ).all()
    )
    if len(profiles) != EXPECTED_PROFILE_COUNT:
        raise ValueError("staging bootstrap did not produce all 30 profiles")
    for profile in profiles:
        media = profile.hero_image
        if (
            not profile.article_details
            or not profile.distribution
            or not profile.sources
            or media.get("kind") != "licensed_photograph"
            or not media.get("attribution")
        ):
            raise ValueError(f"{profile.slug}: canonical profile is incomplete")

    return {
        **result,
        "profiles_review_ready": sum(
            profile.status == "needs_review" for profile in profiles
        ),
        "profiles_published": sum(
            profile.status == "published" for profile in profiles
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-review-required",
        action="store_true",
        help="Acknowledge that import does not approve or publish profiles.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    if settings.environment not in {"staging", "test"}:
        raise SystemExit(
            "This command is restricted to HERBWIRE_ENVIRONMENT=staging or test."
        )
    if not args.confirm_review_required:
        raise SystemExit("--confirm-review-required is mandatory.")
    with get_session_factory()() as session:
        result = bootstrap_staging_corpus(session)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
