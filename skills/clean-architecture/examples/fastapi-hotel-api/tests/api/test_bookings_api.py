"""API tests for /bookings: status codes, response shape and domain error mapping."""

from decimal import Decimal

from fastapi.testclient import TestClient

ROOM_PAYLOAD = {"number": "101", "capacity": 2, "nightly_rate": "100.00"}


def create_room(client: TestClient) -> str:
    room_id: str = client.post("/rooms", json=ROOM_PAYLOAD).json()["id"]
    return room_id


def booking_body(
    room_id: str, check_in: str = "2025-03-01", check_out: str = "2025-03-03"
) -> dict[str, str]:
    return {"room_id": room_id, "guest_name": "Ada", "check_in": check_in, "check_out": check_out}


def test_book_room_returns_201(client: TestClient) -> None:
    room_id = create_room(client)

    response = client.post("/bookings", json=booking_body(room_id))

    assert response.status_code == 201
    body = response.json()
    assert body["room_id"] == room_id
    assert body["check_in"] == "2025-03-01"
    assert Decimal(body["total_price"]) == Decimal("200.00")


def test_unknown_room_returns_404(client: TestClient) -> None:
    assert client.post("/bookings", json=booking_body("missing")).status_code == 404


def test_double_booking_returns_409(client: TestClient) -> None:
    body = booking_body(create_room(client))

    assert client.post("/bookings", json=body).status_code == 201
    assert client.post("/bookings", json=body).status_code == 409


def test_invalid_payload_returns_422(client: TestClient) -> None:
    assert client.post("/bookings", json={"room_id": "x"}).status_code == 422


def test_check_out_not_after_check_in_returns_422(client: TestClient) -> None:
    room_id = create_room(client)

    response = client.post("/bookings", json=booking_body(room_id, "2025-03-03", "2025-03-03"))

    assert response.status_code == 422
    assert response.json() == {"detail": "check_out must be after check_in"}


def test_get_booking_returns_200(client: TestClient) -> None:
    booking_id = client.post("/bookings", json=booking_body(create_room(client))).json()["id"]

    response = client.get(f"/bookings/{booking_id}")

    assert response.status_code == 200
    assert response.json()["id"] == booking_id


def test_cancel_booking_returns_204_then_404(client: TestClient) -> None:
    booking_id = client.post("/bookings", json=booking_body(create_room(client))).json()["id"]

    assert client.delete(f"/bookings/{booking_id}").status_code == 204
    assert client.get(f"/bookings/{booking_id}").status_code == 404
    assert client.delete(f"/bookings/{booking_id}").status_code == 404
