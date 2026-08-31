import base64
import hashlib
import hmac
import json
import time
from typing import Any

from backend.app.core.settings import Settings, get_settings
from fastapi import HTTPException, Request, Response
from starlette import status

SESSION_USER = {"initials": "HB", "label": "Local admin", "role": "Milestone 2 editor"}


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _signature(payload: str, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).digest()
    return _b64encode(digest)


def configured_for_login(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return all(
        [
            settings.admin_email != "admin@example.invalid",
            settings.admin_password != "replace-with-a-local-password",
            settings.session_secret != "replace-with-a-long-random-secret",
            len(settings.session_secret) >= 32,
        ]
    )


def credentials_match(
    email: str, password: str, settings: Settings | None = None
) -> bool:
    settings = settings or get_settings()
    normalized_email = email.strip().casefold()
    expected_email = settings.admin_email.strip().casefold()
    email_ok = hmac.compare_digest(normalized_email, expected_email)
    password_ok = hmac.compare_digest(password, settings.admin_password)
    return email_ok and password_ok


def create_session_cookie_value(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": "local-admin",
        "iat": now,
        "exp": now + settings.session_ttl_seconds,
    }
    encoded_payload = _b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    return f"{encoded_payload}.{_signature(encoded_payload, settings.session_secret)}"


def valid_session(cookie_value: str | None, settings: Settings | None = None) -> bool:
    if not cookie_value:
        return False
    settings = settings or get_settings()
    try:
        encoded_payload, signature = cookie_value.split(".", 1)
        expected_signature = _signature(encoded_payload, settings.session_secret)
        if not hmac.compare_digest(signature, expected_signature):
            return False
        payload = json.loads(_b64decode(encoded_payload))
        return payload.get("sub") == "local-admin" and int(
            payload.get("exp", 0)
        ) >= int(time.time())
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def set_session_cookie(response: Response, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_cookie_value(settings),
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def require_editor_session(request: Request) -> None:
    settings = get_settings()
    if not valid_session(request.cookies.get(settings.session_cookie_name), settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
