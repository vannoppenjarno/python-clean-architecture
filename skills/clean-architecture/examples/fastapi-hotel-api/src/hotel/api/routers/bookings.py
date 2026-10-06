"""API adapter layer: booking endpoints. No business rules, only translation."""

from fastapi import APIRouter, status

from hotel.api.dependencies import BookingServiceDep
from hotel.api.schemas import BookingCreate, BookingOut
from hotel.domain.booking import StayPeriod
from hotel.services.booking_service import BookRoom

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def book_room(body: BookingCreate, service: BookingServiceDep) -> BookingOut:
    command = BookRoom(
        room_id=body.room_id,
        guest_name=body.guest_name,
        period=StayPeriod(body.check_in, body.check_out),
    )
    return BookingOut.from_domain(service.book_room(command))


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: str, service: BookingServiceDep) -> BookingOut:
    return BookingOut.from_domain(service.get_booking(booking_id))


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(booking_id: str, service: BookingServiceDep) -> None:
    service.cancel_booking(booking_id)
