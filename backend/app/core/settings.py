from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="HERBWIRE_",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://herbwire:herbwire_dev@127.0.0.1:5433/herbwire"
    )
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
    zyte_scrapy_cloud_api_key: str | None = Field(default=None)
    zyte_scrapy_cloud_project_id: str | None = Field(default=None)
    zyte_api_key: str | None = Field(default=None)
    zyte_request_timeout_seconds: float = Field(default=10.0)
    zyte_max_retries: int = Field(default=2)

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
