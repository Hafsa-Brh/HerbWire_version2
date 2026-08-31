from backend.app.collectors.providers.zyte import (
    ZyteCollectionProvider,
    ZyteConfigurationError,
    ZyteProviderConfig,
)


def test_zyte_provider_is_safe_when_unconfigured() -> None:
    provider = ZyteCollectionProvider(
        ZyteProviderConfig(
            scrapy_cloud_api_key=None,
            scrapy_cloud_project_id=None,
            zyte_api_key=None,
            timeout_seconds=10,
            max_retries=2,
        )
    )

    assert provider.is_configured() is False

    try:
        provider.collect()
    except ZyteConfigurationError as error:
        assert "not configured" in str(error)
        assert "key" not in str(error).lower() or "api key" not in str(error).lower()
    else:
        raise AssertionError("Unconfigured Zyte provider unexpectedly collected data.")
