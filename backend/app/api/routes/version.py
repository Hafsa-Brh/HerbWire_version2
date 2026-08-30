from backend.app.core.settings import get_settings
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class VersionResponse(BaseModel):
    service: str
    version: str


@router.get("/version", response_model=VersionResponse)
def read_version() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(
        service=settings.service_name, version=settings.service_version
    )
