from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.version import router as version_router
from backend.app.core.settings import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()
app = FastAPI(title="HerbWire API", version=settings.service_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(version_router, prefix="/api/v1", tags=["system"])
app.include_router(health_router, prefix="/api/v1", tags=["system"])
