# ruff: noqa: E501
from dataclasses import dataclass

from backend.app.collectors.providers.base import (
    CollectedDiscoveryRecord,
    CollectionProvider,
)


class ZyteConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ZyteProviderConfig:
    scrapy_cloud_api_key: str | None
    scrapy_cloud_project_id: str | None
    zyte_api_key: str | None
    timeout_seconds: float
    max_retries: int


class ZyteCollectionProvider(CollectionProvider):
    name = "zyte"

    def __init__(self, config: ZyteProviderConfig) -> None:
        self.config = config

    def is_configured(self) -> bool:
        return bool(
            self.config.scrapy_cloud_api_key
            and self.config.scrapy_cloud_project_id
            and self.config.timeout_seconds > 0
            and self.config.max_retries >= 0
        )

    def collect(self) -> list[CollectedDiscoveryRecord]:
        if not self.is_configured():
            raise ZyteConfigurationError(
                "Zyte collection is not configured. Set Scrapy Cloud credentials before live use."
            )
        raise ZyteConfigurationError(
            "Live Zyte collection is intentionally disabled until explicit cloud approval."
        )
