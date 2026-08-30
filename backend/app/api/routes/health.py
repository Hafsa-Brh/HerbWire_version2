from http import HTTPStatus

from backend.app.core.settings import get_settings
from backend.app.db.session import check_database_connection
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str


@router.get("/health", response_model=HealthResponse)
def read_health() -> JSONResponse:
    settings = get_settings()
    is_connected = check_database_connection()
    payload = HealthResponse(
        status="ok" if is_connected else "degraded",
        service=settings.service_name,
        version=settings.service_version,
        database="connected" if is_connected else "disconnected",
    )
    status_code = HTTPStatus.OK if is_connected else HTTPStatus.SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload.model_dump())
