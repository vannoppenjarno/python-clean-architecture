"""API fixtures: a TestClient around an app built by the factory with an in-memory database."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from hotel.api.app import create_app
from hotel.infrastructure.settings import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(Settings(database_url="sqlite://"))
    with TestClient(app) as client:  # runs lifespan -> creates tables
        yield client
