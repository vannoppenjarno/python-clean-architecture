"""API adapter layer: request and response schemas, mapped to and from domain objects."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from hotel.domain.booking import Booking
from hotel.domain.room import Room


class RoomCreate(BaseModel):
    number: str = Field(min_length=1)
    capacity: int = Field(ge=1)
    nightly_rate: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class RoomOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    number: str
    capacity: int
    nightly_rate: Decimal

    @classmethod
    def from_domain(cls, room: Room) -> "RoomOut":
        return cls(
            id=room.id,
            number=room.number,
            capacity=room.capacity,
            nightly_rate=room.nightly_rate,
        )


class BookingCreate(BaseModel):
    room_id: str
    guest_name: str = Field(min_length=1)
    check_in: date
    check_out: date


class BookingOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    room_id: str
    guest_name: str
    check_in: date
    check_out: date
    total_price: Decimal

    @classmethod
    def from_domain(cls, booking: Booking) -> "BookingOut":
        return cls(
            id=booking.id,
            room_id=booking.room_id,
            guest_name=booking.guest_name,
            check_in=booking.period.check_in,
            check_out=booking.period.check_out,
            total_price=booking.total_price,
        )
