"""Unit tests for RoomService, using an in-memory fake for the room repository."""

from decimal import Decimal

from hotel.domain.room import Room
from hotel.services.room_service import RegisterRoom, RoomService
from tests.fakes import InMemoryRoomRepository


def test_register_room_stores_room_with_new_id(room_repository: InMemoryRoomRepository) -> None:
    service = RoomService(room_repository, new_id=lambda: "r1")

    room = service.register_room(RegisterRoom("101", 2, Decimal("120.00")))

    assert room == Room(id="r1", number="101", capacity=2, nightly_rate=Decimal("120.00"))
    assert room_repository.get("r1") == room


def test_list_rooms_returns_registered_rooms(room_repository: InMemoryRoomRepository) -> None:
    ids = iter(["r1", "r2"])
    service = RoomService(room_repository, new_id=lambda: next(ids))
    first = service.register_room(RegisterRoom("101", 2, Decimal("120.00")))
    second = service.register_room(RegisterRoom("102", 4, Decimal("180.00")))

    assert service.list_rooms() == [first, second]


def test_list_rooms_is_empty_without_rooms(room_repository: InMemoryRoomRepository) -> None:
    service = RoomService(room_repository, new_id=lambda: "unused")

    assert service.list_rooms() == []
