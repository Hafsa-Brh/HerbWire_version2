import json

from backend.app.db.session import get_session_factory
from backend.app.domains.discovery.corpus import load_curated_discovery_corpus
from backend.app.domains.discovery.curated_import import import_curated_discoveries


def main() -> None:
    corpus = load_curated_discovery_corpus()
    with get_session_factory()() as session:
        summary = import_curated_discoveries(session, corpus)
    print(json.dumps(summary.__dict__, sort_keys=True))


if __name__ == "__main__":
    main()
