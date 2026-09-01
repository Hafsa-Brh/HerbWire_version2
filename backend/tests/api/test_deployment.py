from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from backend.app.api.routes import editorial
from backend.app.core.auth import (
    clear_failed_logins,
    login_attempt_allowed,
    record_failed_login,
    set_session_cookie,
)
from backend.app.core.settings import Settings
from backend.app.main import create_app
from backend.app.web import runtime_port
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from pydantic import ValidationError


def deployed_settings(**overrides) -> Settings:
    values = {
        "environment": "staging",
        "database_url": "postgres://user@db.example.invalid/herbwire",
        "frontend_origin": "https://herbwire-staging-hafsa.herokuapp.com",
        "admin_email": "editor@example.invalid",
        "admin_password": "long-staging-password",
        "session_secret": "a" * 32,
        "session_cookie_name": "__Host-herbwire_editor_session",
        "session_cookie_secure": True,
        "enable_development_endpoints": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_staging_settings_normalize_heroku_database_url_and_require_ssl() -> None:
    settings = deployed_settings()

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in settings.database_url
    assert settings.allowed_frontend_origins == [
        "https://herbwire-staging-hafsa.herokuapp.com"
    ]


def test_settings_accept_heroku_database_url_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HERBWIRE_DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://user@db.example.invalid/herbwire",
    )

    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("postgresql+psycopg://")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("frontend_origin", ""),
        ("frontend_origin", "http://staging.example.invalid"),
        ("frontend_origin", "https://user@staging.example.invalid"),
        ("frontend_origin", "https://staging.example.invalid/path"),
        ("admin_password", "short"),
        ("session_secret", "short"),
        ("session_cookie_name", "herbwire_editor_session"),
        ("session_cookie_secure", False),
        ("enable_development_endpoints", True),
    ],
)
def test_staging_settings_reject_unsafe_values(field: str, value) -> None:
    with pytest.raises(ValidationError, match="Invalid deployed runtime configuration"):
        deployed_settings(**{field: value})


def test_runtime_port_uses_heroku_port_and_rejects_invalid_values() -> None:
    assert runtime_port({"PORT": "4321"}) == 4321
    assert runtime_port({}) == 8000
    with pytest.raises(ValueError, match="PORT must be an integer"):
        runtime_port({"PORT": "not-a-port"})
    with pytest.raises(ValueError, match="between 1 and 65535"):
        runtime_port({"PORT": "70000"})


def test_compiled_frontend_serves_assets_and_spa_without_intercepting_api() -> None:
    with TemporaryDirectory(prefix=".herbwire-static-test-", dir=Path.cwd()) as temp:
        static_dir = Path(temp)
        (static_dir / "assets").mkdir()
        (static_dir / "index.html").write_text(
            "<!doctype html><title>HerbWire staging</title>", encoding="utf-8"
        )
        (static_dir / "assets" / "app.js").write_text(
            "console.log('herbwire')", encoding="utf-8"
        )

        with TestClient(create_app(frontend_dist=static_dir)) as client:
            root = client.get("/")
            spa_route = client.get("/plants/peppermint")
            asset = client.get("/assets/app.js")
            unknown_api = client.get("/api/v1/not-a-route")

    assert root.status_code == 200
    assert spa_route.status_code == 200
    assert "HerbWire staging" in spa_route.text
    assert asset.status_code == 200
    assert "console.log" in asset.text
    assert unknown_api.status_code == 404
    assert "HerbWire staging" not in unknown_api.text


def test_staging_cookie_is_secure_httponly_host_scoped_and_lax() -> None:
    response = Response()
    set_session_cookie(response, deployed_settings())

    cookie = response.headers["set-cookie"]
    assert "__Host-herbwire_editor_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Domain=" not in cookie


def test_login_failure_throttle_blocks_after_five_attempts() -> None:
    key = "deployment-throttle-test"
    clear_failed_logins(key)
    try:
        for _ in range(5):
            assert login_attempt_allowed(key)
            record_failed_login(key)
        assert not login_attempt_allowed(key)
    finally:
        clear_failed_logins(key)


def test_development_editorial_endpoints_are_hidden_in_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(editorial, "get_settings", deployed_settings)

    with pytest.raises(HTTPException) as error:
        editorial.require_development_endpoint()

    assert error.value.status_code == 404


def test_heroku_manifest_uses_one_web_image_and_migration_release() -> None:
    manifest = Path("heroku.yml").read_text(encoding="utf-8")

    assert manifest.count("web:") == 2
    assert "worker:" not in manifest
    assert "python -m alembic -c backend/alembic.ini upgrade head" in manifest
    assert "python -m backend.app.web" in manifest
