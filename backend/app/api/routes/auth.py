from backend.app.api.schemas import LoginRequest, SessionResponse, SessionUserResponse
from backend.app.core.auth import (
    SESSION_USER,
    clear_session_cookie,
    configured_for_login,
    credentials_match,
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
def login(request: LoginRequest, response: Response) -> SessionResponse:
    settings = get_settings()
    if not configured_for_login(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Editorial login is not configured.",
        )
    if not credentials_match(request.email, request.password, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
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
