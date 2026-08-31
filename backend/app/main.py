from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.editorial import router as editorial_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.newsletter import router as newsletter_router
from backend.app.api.routes.plants import router as plants_router
from backend.app.api.routes.version import router as version_router
from backend.app.core.settings import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()
app = FastAPI(title="HerbWire API", version=settings.service_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(version_router, prefix="/api/v1", tags=["system"])
app.include_router(health_router, prefix="/api/v1", tags=["system"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(newsletter_router, prefix="/api/v1", tags=["newsletter"])
app.include_router(plants_router, prefix="/api/v1", tags=["plants"])
app.include_router(editorial_router, prefix="/api/v1", tags=["editorial"])
