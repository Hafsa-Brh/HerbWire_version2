from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="HERBWIRE_",
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = Field(
        default="postgresql+psycopg://herbwire:herbwire_dev@127.0.0.1:5433/herbwire",
        validation_alias=AliasChoices("HERBWIRE_DATABASE_URL", "DATABASE_URL"),
    )
    local_database_name: str | None = Field(default=None, pattern=r"^[a-z0-9_]+$")
    frontend_origin: str = Field(default="http://127.0.0.1:5173")
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    service_name: str = "herbwire-api"
    service_version: str = "0.1.0"
    admin_email: str = Field(default="admin@example.invalid")
    admin_password: str = Field(default="replace-with-a-local-password")
    session_secret: str = Field(default="replace-with-a-long-random-secret")
    session_cookie_name: str = Field(default="herbwire_editor_session")
    session_ttl_seconds: int = Field(default=60 * 60 * 8)
    session_cookie_secure: bool = Field(default=False)
    enable_development_endpoints: bool = Field(default=True)
    zyte_scrapy_cloud_api_key: str | None = Field(default=None)
    zyte_scrapy_cloud_project_id: str | None = Field(default=None)
    zyte_api_key: str | None = Field(default=None)
    zyte_request_timeout_seconds: float = Field(default=10.0)
    zyte_max_retries: int = Field(default=2)
    ncbi_email: str | None = Field(default=None)
    ncbi_request_timeout_seconds: float = Field(default=10.0)
    ncbi_max_retries: int = Field(default=2)

    @model_validator(mode="after")
    def validate_runtime_contract(self) -> Self:
        database_url = make_url(self.database_url)
        if database_url.drivername in {"postgres", "postgresql"}:
            database_url = database_url.set(drivername="postgresql+psycopg")

        if self.local_database_name:
            if self.environment != "local":
                raise ValueError(
                    "HERBWIRE_LOCAL_DATABASE_NAME is permitted only for local runtime"
                )
            database_url = database_url.set(database=self.local_database_name)

        if self.environment in {"staging", "production"}:
            database_url = database_url.update_query_dict({"sslmode": "require"})
            errors: list[str] = []
            if database_url.drivername != "postgresql+psycopg":
                errors.append("DATABASE_URL must select PostgreSQL through psycopg")
            frontend_origin = self.frontend_origin.strip()
            parsed_frontend_origin = urlparse(frontend_origin)
            if (
                parsed_frontend_origin.scheme != "https"
                or not parsed_frontend_origin.netloc
                or parsed_frontend_origin.username is not None
                or parsed_frontend_origin.password is not None
                or parsed_frontend_origin.path not in {"", "/"}
                or parsed_frontend_origin.params
                or parsed_frontend_origin.query
                or parsed_frontend_origin.fragment
            ):
                errors.append(
                    "HERBWIRE_FRONTEND_ORIGIN must be an HTTPS origin without a path"
                )
            if not configured_admin_email(self.admin_email):
                errors.append("HERBWIRE_ADMIN_EMAIL must be explicitly configured")
            if len(self.admin_password) < 16:
                errors.append(
                    "HERBWIRE_ADMIN_PASSWORD must contain at least 16 characters"
                )
            if len(self.session_secret) < 32:
                errors.append(
                    "HERBWIRE_SESSION_SECRET must contain at least 32 characters"
                )
            if not self.session_cookie_secure:
                errors.append("HERBWIRE_SESSION_COOKIE_SECURE must be true")
            if not self.session_cookie_name.startswith("__Host-"):
                errors.append(
                    "HERBWIRE_SESSION_COOKIE_NAME must use the __Host- prefix"
                )
            if self.enable_development_endpoints:
                errors.append("HERBWIRE_ENABLE_DEVELOPMENT_ENDPOINTS must be false")
            if errors:
                raise ValueError(
                    "Invalid deployed runtime configuration: " + "; ".join(errors)
                )

        self.database_url = database_url.render_as_string(hide_password=False)
        if self.environment in {"staging", "production"}:
            self.frontend_origin = self.frontend_origin.strip().rstrip("/")
        return self

    @property
    def allowed_frontend_origins(self) -> list[str]:
        origins = {
            origin.strip().rstrip("/") for origin in self.frontend_origin.split(",")
        }
        origins.discard("")

        for origin in list(origins):
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or parsed.port != 5173:
                continue
            if parsed.hostname == "localhost":
                origins.add(f"{parsed.scheme}://127.0.0.1:{parsed.port}")
            if parsed.hostname == "127.0.0.1":
                origins.add(f"{parsed.scheme}://localhost:{parsed.port}")

        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configured_admin_email(value: str) -> bool:
    normalized = value.strip().casefold()
    return bool(normalized and normalized != "admin@example.invalid")
