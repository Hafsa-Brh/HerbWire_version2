from backend.app.api.schemas import LoginRequest, SessionResponse, SessionUserResponse
from backend.app.core.auth import (
    SESSION_USER,
    clear_failed_logins,
    clear_session_cookie,
    configured_for_login,
    credentials_match,
    login_attempt_allowed,
    record_failed_login,
    set_session_cookie,
    valid_session,
)
from backend.app.core.settings import get_settings
from fastapi import APIRouter, HTTPException, Request, Response
from starlette import status

router = APIRouter(prefix="/auth")


def _session_response(authenticated: bool) -> SessionResponse:
    return SessionResponse(
        authenticated=authenticated,
        user=SessionUserResponse(**SESSION_USER) if authenticated else None,
    )


@router.post("/login", response_model=SessionResponse)
def login(
    credentials: LoginRequest, request: Request, response: Response
) -> SessionResponse:
    settings = get_settings()
    if not configured_for_login(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Editorial login is not configured.",
        )
    login_key = request.client.host if request.client else "unknown"
    if not login_attempt_allowed(login_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )
    if not credentials_match(credentials.email, credentials.password, settings):
        record_failed_login(login_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    clear_failed_logins(login_key)
    set_session_cookie(response, settings)
    return _session_response(True)


@router.post("/logout", response_model=SessionResponse)
def logout(response: Response) -> SessionResponse:
    clear_session_cookie(response)
    return _session_response(False)


@router.get("/session", response_model=SessionResponse)
def session(request: Request) -> SessionResponse:
    settings = get_settings()
    return _session_response(
        valid_session(request.cookies.get(settings.session_cookie_name), settings)
    )
