"""Services layer: use cases for booking, looking up and cancelling stays."""

from dataclasses import dataclass

from hotel.domain.booking import Booking, StayPeriod
from hotel.domain.errors import BookingNotFound, RoomNotFound, RoomUnavailable
from hotel.repositories.bookings import BookingRepository
from hotel.repositories.rooms import RoomRepository
from hotel.services.ports import IdFactory


@dataclass(frozen=True)
class BookRoom:
    """Input command for the book-room use case."""

    room_id: str
    guest_name: str
    period: StayPeriod


class BookingService:
    def __init__(
        self,
        rooms: RoomRepository,
        bookings: BookingRepository,
        new_id: IdFactory,
    ) -> None:
        self._rooms = rooms
        self._bookings = bookings
        self._new_id = new_id

    def book_room(self, command: BookRoom) -> Booking:
        room = self._rooms.get(command.room_id)
        if room is None:
            raise RoomNotFound(command.room_id)
        if self._bookings.find_overlapping(room.id, command.period):
            raise RoomUnavailable(room.id, command.period)

        booking = Booking(
            id=self._new_id(),
            room_id=room.id,
            guest_name=command.guest_name,
            period=command.period,
            total_price=room.price_for(command.period),
        )
        self._bookings.add(booking)
        return booking

    def get_booking(self, booking_id: str) -> Booking:
        booking = self._bookings.get(booking_id)
        if booking is None:
            raise BookingNotFound(booking_id)
        return booking

    def cancel_booking(self, booking_id: str) -> None:
        if self._bookings.get(booking_id) is None:
            raise BookingNotFound(booking_id)
        self._bookings.remove(booking_id)
