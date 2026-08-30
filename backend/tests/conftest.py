from collections.abc import Iterator

import pytest
from backend.app.core.settings import get_settings
from backend.app.db.session import dispose_engine
from backend.app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_runtime_state() -> Iterator[None]:
    get_settings.cache_clear()
    dispose_engine()
    yield
    dispose_engine()
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
