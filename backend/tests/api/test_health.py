import pytest
from backend.app.api.routes import health as health_routes
from backend.app.db import session as session_module
from sqlalchemy.exc import SQLAlchemyError


def test_health_reports_connected_database(client, monkeypatch) -> None:
    monkeypatch.setattr(health_routes, "check_database_connection", lambda: True)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "herbwire-api",
        "version": "0.1.0",
        "database": "connected",
    }


def test_health_reports_database_disconnect_without_leaking_details(
    client, monkeypatch
) -> None:
    def broken_engine():
        raise SQLAlchemyError("password=super-secret")

    monkeypatch.setattr(session_module, "get_engine", broken_engine)

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "service": "herbwire-api",
        "version": "0.1.0",
        "database": "disconnected",
    }
    assert "super-secret" not in response.text
    assert "password" not in response.text


def test_health_reports_degraded_when_database_check_returns_false(
    client, monkeypatch
) -> None:
    monkeypatch.setattr(health_routes, "check_database_connection", lambda: False)

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["database"] == "disconnected"


def test_health_does_not_hide_non_database_programming_errors(
    client, monkeypatch
) -> None:
    def broken_check() -> bool:
        raise ValueError("unexpected bug")

    monkeypatch.setattr(health_routes, "check_database_connection", broken_check)

    with pytest.raises(ValueError, match="unexpected bug"):
        client.get("/api/v1/health")
