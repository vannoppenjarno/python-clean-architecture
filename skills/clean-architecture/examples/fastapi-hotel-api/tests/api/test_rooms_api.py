"""API tests for /rooms: status codes, response shape and validation."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


def test_register_room_returns_201(client: TestClient) -> None:
    payload = {"number": "101", "capacity": 2, "nightly_rate": "100.00"}

    response = client.post("/rooms", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["number"] == "101"
    assert body["capacity"] == 2
    assert Decimal(body["nightly_rate"]) == Decimal("100.00")


def test_list_rooms_returns_registered_rooms(client: TestClient) -> None:
    client.post("/rooms", json={"number": "101", "capacity": 2, "nightly_rate": "100.00"})
    client.post("/rooms", json={"number": "102", "capacity": 4, "nightly_rate": "150.00"})

    response = client.get("/rooms")

    assert response.status_code == 200
    assert [room["number"] for room in response.json()] == ["101", "102"]


@pytest.mark.parametrize(
    "payload",
    [
        {"number": "101", "capacity": 0, "nightly_rate": "100.00"},
        {"number": "101", "capacity": 2, "nightly_rate": "0"},
        {"number": "", "capacity": 2, "nightly_rate": "100.00"},
        {"number": "101"},
    ],
    ids=["zero-capacity", "zero-rate", "empty-number", "missing-fields"],
)
def test_invalid_room_payload_returns_422(client: TestClient, payload: dict[str, object]) -> None:
    assert client.post("/rooms", json=payload).status_code == 422
