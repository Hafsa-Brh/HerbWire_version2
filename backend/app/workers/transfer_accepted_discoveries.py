import argparse
import json

from backend.app.db.session import get_session_factory
from backend.app.domains.discovery.accepted_transfer import (
    transfer_owner_accepted_discoveries,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transfer the versioned owner-accepted Discovery publication state."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate corpus, manifest, dependencies, and target without writes.",
    )
    args = parser.parse_args()
    with get_session_factory()() as session:
        summary = transfer_owner_accepted_discoveries(session, dry_run=args.dry_run)
    print(json.dumps(summary.__dict__, sort_keys=True))


if __name__ == "__main__":
    main()
