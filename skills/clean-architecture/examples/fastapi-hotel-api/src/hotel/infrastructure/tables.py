"""Infrastructure layer: SQLModel persistence models. They never leave this layer."""

from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel


class RoomTable(SQLModel, table=True):
    __tablename__ = "rooms"

    id: str = Field(primary_key=True)
    number: str = Field(index=True)
    capacity: int
    nightly_rate: Decimal = Field(max_digits=10, decimal_places=2)


class BookingTable(SQLModel, table=True):
    __tablename__ = "bookings"

    id: str = Field(primary_key=True)
    room_id: str = Field(foreign_key="rooms.id", index=True)
    guest_name: str
    check_in: date
    check_out: date
    total_price: Decimal = Field(max_digits=10, decimal_places=2)
