from urllib.parse import urlunsplit

from backend.app.core.settings import Settings
from starlette.datastructures import URL
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response


class CanonicalOriginMiddleware(BaseHTTPMiddleware):
    """Canonicalize only configured custom hosts while preserving recovery hosts."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        canonical_host = self.settings.canonical_host
        public_site_url = self.settings.public_site_url
        if not canonical_host or not public_site_url:
            return await call_next(request)

        host = (request.url.hostname or "").lower()
        custom_hosts = {canonical_host, f"www.{canonical_host}"}
        if host not in custom_hosts:
            return await call_next(request)

        scheme = request.url.scheme
        if (
            self.settings.environment in {"staging", "production"}
            and self.settings.trust_proxy_headers
        ):
            forwarded = request.headers.get("x-forwarded-proto", "")
            candidate = forwarded.split(",", 1)[0].strip().lower()
            if candidate in {"http", "https"}:
                scheme = candidate

        if host != canonical_host or scheme != "https":
            canonical = URL(public_site_url)
            target = urlunsplit(
                (
                    canonical.scheme,
                    canonical.netloc,
                    request.url.path,
                    request.url.query,
                    "",
                )
            )
            return RedirectResponse(target, status_code=308)
        return await call_next(request)
