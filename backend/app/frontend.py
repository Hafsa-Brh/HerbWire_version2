from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    """Serve a compiled SPA without turning unknown API paths into HTML."""

    async def get_response(self, path: str, scope: dict) -> Response:
        request_path = str(scope.get("path", "")).lstrip("/")
        is_api_path = (
            path == "api"
            or path.startswith("api/")
            or request_path == "api"
            or request_path.startswith("api/")
        )
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if is_api_path or error.status_code != 404:
                raise
            return FileResponse(Path(str(self.directory)) / "index.html")
        if is_api_path or response.status_code != 404:
            return response
        return FileResponse(Path(str(self.directory)) / "index.html")


def mount_frontend(app: FastAPI, directory: Path) -> bool:
    index_path = directory / "index.html"
    if not index_path.is_file():
        return False
    app.mount("/", SPAStaticFiles(directory=directory, html=True), name="frontend")
    return True
