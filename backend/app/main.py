from pathlib import Path

from backend.app.api.routes.admin_catalog import router as admin_catalog_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.discoveries import router as discoveries_router
from backend.app.api.routes.discovery_editorial import (
    router as discovery_editorial_router,
)
from backend.app.api.routes.editorial import router as editorial_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.materials import router as materials_router
from backend.app.api.routes.newsletter import router as newsletter_router
from backend.app.api.routes.plants import router as plants_router
from backend.app.api.routes.version import router as version_router
from backend.app.core.settings import get_settings
from backend.app.frontend import mount_frontend
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DEFAULT_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(frontend_dist: Path | None = None) -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="HerbWire API", version=settings.service_version)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(version_router, prefix="/api/v1", tags=["system"])
    application.include_router(health_router, prefix="/api/v1", tags=["system"])
    application.include_router(auth_router, prefix="/api/v1", tags=["auth"])
    application.include_router(newsletter_router, prefix="/api/v1", tags=["newsletter"])
    application.include_router(plants_router, prefix="/api/v1", tags=["plants"])
    application.include_router(materials_router, prefix="/api/v1", tags=["materials"])
    application.include_router(
        discoveries_router, prefix="/api/v1", tags=["discoveries"]
    )
    application.include_router(editorial_router, prefix="/api/v1", tags=["editorial"])
    application.include_router(
        admin_catalog_router, prefix="/api/v1", tags=["editorial"]
    )
    application.include_router(
        discovery_editorial_router, prefix="/api/v1", tags=["editorial"]
    )
    mount_frontend(application, frontend_dist or DEFAULT_FRONTEND_DIST)
    return application


app = create_app()
