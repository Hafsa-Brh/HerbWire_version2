from html import escape
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, Response
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    """Serve a compiled SPA without turning unknown API paths into HTML."""

    def __init__(self, *args, public_site_url: str | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.public_site_url = public_site_url

    def _index_response(self, scope: dict) -> HTMLResponse:
        index_path = Path(str(self.directory)) / "index.html"
        html = index_path.read_text(encoding="utf-8")
        path = str(scope.get("path", "/")) or "/"
        is_private = path == "/login" or path.startswith("/admin")
        public_prefixes = (
            "/plants",
            "/discoveries",
            "/materials-and-craft",
            "/field-cabinet",
        )
        is_public = path == "/" or path.startswith(public_prefixes)
        metadata = ""
        if is_private:
            metadata = '<meta name="robots" content="noindex,nofollow" />'
        elif self.public_site_url and is_public:
            href = f"{self.public_site_url.rstrip('/')}{path}"
            metadata = f'<link rel="canonical" href="{escape(href, quote=True)}" />'
        if metadata:
            html = html.replace("</head>", f"    {metadata}\n  </head>", 1)
        return HTMLResponse(html)

    async def get_response(self, path: str, scope: dict) -> Response:
        request_path = str(scope.get("path", "")).lstrip("/")
        is_api_path = (
            path == "api"
            or path.startswith("api/")
            or request_path == "api"
            or request_path.startswith("api/")
        )
        if path in {"", "."}:
            return self._index_response(scope)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if is_api_path or error.status_code != 404:
                raise
            return self._index_response(scope)
        if is_api_path or response.status_code != 404:
            return response
        return self._index_response(scope)


def mount_frontend(
    app: FastAPI, directory: Path, public_site_url: str | None = None
) -> bool:
    index_path = directory / "index.html"
    if not index_path.is_file():
        return False
    app.mount(
        "/",
        SPAStaticFiles(directory=directory, html=True, public_site_url=public_site_url),
        name="frontend",
    )
    return True
