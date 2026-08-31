from backend.app.db.session import get_session_factory
from backend.app.domains.pipeline.fixture_pipeline import run_fixture_pipeline


def main() -> None:
    with get_session_factory()() as session:
        run = run_fixture_pipeline(session)
    print({"run_id": str(run.id), "status": run.status, "summary": run.summary})


if __name__ == "__main__":
    main()
