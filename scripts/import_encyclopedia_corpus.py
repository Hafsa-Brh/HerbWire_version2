"""Validate and import the versioned curated encyclopedia corpus."""

import argparse
import json

from backend.app.db.session import get_session_factory
from backend.app.domains.encyclopedia.corpus import load_corpus
from backend.app.domains.encyclopedia.service import seed_curated_profiles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=("A", "B", "C"))
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the corpus without connecting to PostgreSQL.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_corpus()
    selected = [
        profile
        for profile in manifest.profiles
        if args.batch is None or profile.batch == args.batch
    ]
    if args.validate_only:
        print(
            json.dumps(
                {
                    "profiles_validated": len(selected),
                    "sources_validated": len(manifest.sources),
                    "batch": args.batch,
                },
                sort_keys=True,
            )
        )
        return

    with get_session_factory()() as session:
        result = seed_curated_profiles(session, batch=args.batch)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
