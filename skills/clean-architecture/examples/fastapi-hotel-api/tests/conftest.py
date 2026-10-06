"""Shared fixtures: a fresh in-memory fake per test, so no state leaks between tests."""

import pytest

from tests.fakes import InMemoryRoomRepository


@pytest.fixture
def room_repository() -> InMemoryRoomRepository:
    return InMemoryRoomRepository()
