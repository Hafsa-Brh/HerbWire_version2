import json
import sys

from backend.app.db.session import get_session_factory
from backend.app.domains.discovery.corpus import (
    load_curated_discovery_corpus,
    load_new_plant_discovery_corpus,
)
from backend.app.domains.discovery.curated_import import import_curated_discoveries


def main() -> None:
    loaders = {
        "milestone-4b": load_curated_discovery_corpus,
        "milestone-4c": load_new_plant_discovery_corpus,
    }
    requested = sys.argv[1] if len(sys.argv) > 1 else "milestone-4b"
    if requested not in loaders:
        raise SystemExit(
            "usage: import_curated_discoveries.py [milestone-4b|milestone-4c]"
        )
    corpus = loaders[requested]()
    with get_session_factory()() as session:
        summary = import_curated_discoveries(session, corpus)
    print(json.dumps(summary.__dict__, sort_keys=True))


if __name__ == "__main__":
    main()
