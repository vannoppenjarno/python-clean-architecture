"""Infrastructure layer: SQLModel implementations of the repository ports, with explicit mapping."""

from sqlmodel import Session, col, select

from hotel.domain.booking import Booking, StayPeriod
from hotel.domain.room import Room
from hotel.infrastructure.tables import BookingTable, RoomTable


class SqlModelRoomRepository:
    """Implements repositories.rooms.RoomRepository (structurally)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, room: Room) -> None:
        self._session.add(_room_to_row(room))
        self._session.commit()

    def get(self, room_id: str) -> Room | None:
        row = self._session.get(RoomTable, room_id)
        return _room_to_domain(row) if row else None

    def list_all(self) -> list[Room]:
        statement = select(RoomTable).order_by(col(RoomTable.number))
        return [_room_to_domain(row) for row in self._session.exec(statement)]


class SqlModelBookingRepository:
    """Implements repositories.bookings.BookingRepository (structurally)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, booking: Booking) -> None:
        self._session.add(_booking_to_row(booking))
        self._session.commit()

    def get(self, booking_id: str) -> Booking | None:
        row = self._session.get(BookingTable, booking_id)
        return _booking_to_domain(row) if row else None

    def find_overlapping(self, room_id: str, period: StayPeriod) -> list[Booking]:
        statement = select(BookingTable).where(
            BookingTable.room_id == room_id,
            col(BookingTable.check_in) < period.check_out,
            col(BookingTable.check_out) > period.check_in,
        )
        return [_booking_to_domain(row) for row in self._session.exec(statement)]

    def remove(self, booking_id: str) -> None:
        row = self._session.get(BookingTable, booking_id)
        if row is not None:
            self._session.delete(row)
            self._session.commit()


def _room_to_domain(row: RoomTable) -> Room:
    return Room(
        id=row.id,
        number=row.number,
        capacity=row.capacity,
        nightly_rate=row.nightly_rate,
    )


def _room_to_row(room: Room) -> RoomTable:
    return RoomTable(
        id=room.id,
        number=room.number,
        capacity=room.capacity,
        nightly_rate=room.nightly_rate,
    )


def _booking_to_domain(row: BookingTable) -> Booking:
    return Booking(
        id=row.id,
        room_id=row.room_id,
        guest_name=row.guest_name,
        period=StayPeriod(row.check_in, row.check_out),
        total_price=row.total_price,
    )


def _booking_to_row(booking: Booking) -> BookingTable:
    return BookingTable(
        id=booking.id,
        room_id=booking.room_id,
        guest_name=booking.guest_name,
        check_in=booking.period.check_in,
        check_out=booking.period.check_out,
        total_price=booking.total_price,
    )
