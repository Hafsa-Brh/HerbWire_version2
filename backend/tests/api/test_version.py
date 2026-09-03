from collections.abc import Iterator

import pytest
from backend.app.core.settings import Settings, get_settings


@pytest.fixture
def isolated_settings_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in (
        "HERBWIRE_DATABASE_URL",
        "HERBWIRE_LOCAL_DATABASE_NAME",
        "HERBWIRE_FRONTEND_ORIGIN",
        "HERBWIRE_API_HOST",
        "HERBWIRE_API_PORT",
    ):
        monkeypatch.delenv(key, raising=False)

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_defaults_match_documented_local_runtime_contract(
    isolated_settings_environment: None,
) -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url == (
        "postgresql+psycopg://herbwire:herbwire_dev@127.0.0.1:5433/herbwire"
    )
    assert settings.frontend_origin == "http://127.0.0.1:5173"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000


def test_get_settings_respects_explicit_database_url_override(
    isolated_settings_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "HERBWIRE_DATABASE_URL",
        "postgresql+psycopg://herbwire:herbwire_dev@127.0.0.1:5432/herbwire",
    )

    settings = get_settings()

    assert (
        settings.database_url
        == "postgresql+psycopg://herbwire:herbwire_dev@127.0.0.1:5432/herbwire"
    )


def test_version_returns_expected_payload(client) -> None:
    response = client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {
        "service": get_settings().service_name,
        "version": get_settings().service_version,
    }


def test_version_preflight_includes_configured_cors_origin(client) -> None:
    response = client.options(
        "/api/v1/version",
        headers={
            "Origin": get_settings().frontend_origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == get_settings().frontend_origin
    )
