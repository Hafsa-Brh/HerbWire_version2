import os
from collections.abc import Iterator

import pytest
from backend.app.core.settings import get_settings
from backend.app.db.session import dispose_engine
from backend.app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url


def _assert_safe_backend_test_target() -> None:
    allow_destructive_tests = (
        os.getenv("HERBWIRE_ALLOW_DESTRUCTIVE_TEST_DB", "").lower() == "true"
    )
    if not allow_destructive_tests:
        pytest.exit(
            "HERBWIRE_ALLOW_DESTRUCTIVE_TEST_DB=true is required for backend tests "
            "because the suite mutates the configured database.",
            returncode=2,
        )

    database_name = make_url(get_settings().database_url).database or ""
    if os.getenv("GITHUB_ACTIONS") != "true" and database_name == "herbwire":
        pytest.exit(
            "Refusing to run backend tests against the local 'herbwire' database. "
            "Use 'herbwire_m2_migration_verify' for local destructive verification.",
            returncode=2,
        )


@pytest.fixture(scope="session", autouse=True)
def guard_backend_test_database() -> None:
    get_settings.cache_clear()
    _assert_safe_backend_test_target()


@pytest.fixture(autouse=True)
def reset_runtime_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("HERBWIRE_ADMIN_EMAIL", "test-admin@example.invalid")
    monkeypatch.setenv("HERBWIRE_ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv(
        "HERBWIRE_SESSION_SECRET", "test-session-secret-with-enough-length"
    )
    get_settings.cache_clear()
    dispose_engine()
    yield
    dispose_engine()
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
