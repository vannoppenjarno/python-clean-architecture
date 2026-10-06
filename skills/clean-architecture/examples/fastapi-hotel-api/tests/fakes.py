"""Test doubles and test data: in-memory implementations of the repository ports."""

from decimal import Decimal

from hotel.domain.booking import Booking, StayPeriod
from hotel.domain.room import Room

ROOM_101 = Room(id="r1", number="101", capacity=2, nightly_rate=Decimal("120.00"))


def make_booking(booking_id: str, period: StayPeriod, room: Room = ROOM_101) -> Booking:
    return Booking(
        id=booking_id,
        room_id=room.id,
        guest_name="Ada",
        period=period,
        total_price=room.price_for(period),
    )


class InMemoryRoomRepository:
    def __init__(self, rooms: list[Room] | None = None) -> None:
        self._rooms = {room.id: room for room in rooms or []}

    def add(self, room: Room) -> None:
        self._rooms[room.id] = room

    def get(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def list_all(self) -> list[Room]:
        return list(self._rooms.values())


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self.bookings: dict[str, Booking] = {}

    def add(self, booking: Booking) -> None:
        self.bookings[booking.id] = booking

    def get(self, booking_id: str) -> Booking | None:
        return self.bookings.get(booking_id)

    def find_overlapping(self, room_id: str, period: StayPeriod) -> list[Booking]:
        return [
            b for b in self.bookings.values()
            if b.room_id == room_id and b.period.overlaps(period)
        ]

    def remove(self, booking_id: str) -> None:
        self.bookings.pop(booking_id, None)
