from backend.app.core.settings import get_settings


def test_settings_defaults_match_documented_local_runtime_contract() -> None:
    settings = get_settings()

    assert settings.database_url == (
        "postgresql+psycopg://herbwire:herbwire_dev@127.0.0.1:5433/herbwire"
    )
    assert settings.frontend_origin == "http://127.0.0.1:5173"


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
