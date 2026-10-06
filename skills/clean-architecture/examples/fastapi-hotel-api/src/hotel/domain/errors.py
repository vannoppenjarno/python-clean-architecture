"""Domain layer: business errors. They carry no HTTP or database meaning."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hotel.domain.booking import StayPeriod


class DomainError(Exception):
    """Base class for all business rule violations."""


class InvalidStayPeriod(DomainError):
    """A stay period breaks its invariants, for example check-out before check-in."""


class RoomNotFound(DomainError):
    def __init__(self, room_id: str) -> None:
        super().__init__(f"Room {room_id!r} does not exist")
        self.room_id = room_id


class BookingNotFound(DomainError):
    def __init__(self, booking_id: str) -> None:
        super().__init__(f"Booking {booking_id!r} does not exist")
        self.booking_id = booking_id


class RoomUnavailable(DomainError):
    def __init__(self, room_id: str, period: StayPeriod) -> None:
        super().__init__(
            f"Room {room_id!r} is already booked between "
            f"{period.check_in.isoformat()} and {period.check_out.isoformat()}"
        )
        self.room_id = room_id
        self.period = period
