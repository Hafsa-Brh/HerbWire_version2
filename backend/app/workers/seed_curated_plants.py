from backend.app.db.session import get_session_factory
from backend.app.domains.encyclopedia.service import seed_curated_profiles


def main() -> None:
    with get_session_factory()() as session:
        result = seed_curated_profiles(session)
    print(result)


if __name__ == "__main__":
    main()
