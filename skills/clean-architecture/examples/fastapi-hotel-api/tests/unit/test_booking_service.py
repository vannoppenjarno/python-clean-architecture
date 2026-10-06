"""Unit tests for BookingService, using in-memory fakes for the ports."""

from datetime import date
from decimal import Decimal

import pytest

from hotel.domain.booking import StayPeriod
from hotel.domain.errors import BookingNotFound, RoomNotFound, RoomUnavailable
from hotel.domain.room import Room
from hotel.services.booking_service import BookingService, BookRoom
from tests.fakes import ROOM_101, InMemoryBookingRepository, InMemoryRoomRepository

MARCH_1_TO_3 = StayPeriod(date(2025, 3, 1), date(2025, 3, 3))


def make_service(*rooms: Room) -> tuple[BookingService, InMemoryBookingRepository]:
    bookings = InMemoryBookingRepository()
    ids = iter(f"b{n}" for n in range(1, 100))
    service = BookingService(
        InMemoryRoomRepository(list(rooms)), bookings, new_id=lambda: next(ids)
    )
    return service, bookings


def test_book_room_stores_priced_booking() -> None:
    service, bookings = make_service(ROOM_101)

    booking = service.book_room(BookRoom("r1", "Ada", MARCH_1_TO_3))

    assert booking.id == "b1"
    assert booking.total_price == Decimal("240.00")
    assert bookings.get("b1") == booking


def test_book_room_rejects_overlap() -> None:
    service, _ = make_service(ROOM_101)
    service.book_room(BookRoom("r1", "Ada", MARCH_1_TO_3))

    with pytest.raises(RoomUnavailable):
        service.book_room(BookRoom("r1", "Bob", StayPeriod(date(2025, 3, 2), date(2025, 3, 5))))


def test_book_room_allows_back_to_back_stays() -> None:
    service, bookings = make_service(ROOM_101)
    service.book_room(BookRoom("r1", "Ada", MARCH_1_TO_3))

    service.book_room(BookRoom("r1", "Bob", StayPeriod(date(2025, 3, 3), date(2025, 3, 5))))

    assert len(bookings.bookings) == 2


def test_book_room_rejects_unknown_room() -> None:
    service, bookings = make_service()

    with pytest.raises(RoomNotFound):
        service.book_room(BookRoom("missing", "Ada", MARCH_1_TO_3))

    assert bookings.bookings == {}


def test_get_booking_returns_stored_booking() -> None:
    service, _ = make_service(ROOM_101)
    booking = service.book_room(BookRoom("r1", "Ada", MARCH_1_TO_3))

    assert service.get_booking("b1") == booking


def test_get_booking_raises_when_missing() -> None:
    service, _ = make_service(ROOM_101)

    with pytest.raises(BookingNotFound):
        service.get_booking("missing")


def test_cancel_booking_removes_it() -> None:
    service, bookings = make_service(ROOM_101)
    service.book_room(BookRoom("r1", "Ada", MARCH_1_TO_3))

    service.cancel_booking("b1")

    assert bookings.get("b1") is None


def test_cancel_booking_raises_when_missing() -> None:
    service, _ = make_service(ROOM_101)

    with pytest.raises(BookingNotFound):
        service.cancel_booking("missing")
