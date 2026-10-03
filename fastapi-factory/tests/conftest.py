from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from fastapi_factory.config import Settings
from fastapi_factory.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    # A brand-new app per test, built with test settings
    app = create_app(Settings(environment="test"))
    with TestClient(app) as c:
        yield c
