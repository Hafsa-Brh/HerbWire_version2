from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
