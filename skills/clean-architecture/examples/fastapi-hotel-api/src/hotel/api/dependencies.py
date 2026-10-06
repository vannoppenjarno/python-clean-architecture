"""API adapter layer: the composition root. The only place that wires concrete classes."""

from collections.abc import Iterator
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request
from sqlmodel import Session

from hotel.infrastructure.sqlmodel_repositories import (
    SqlModelBookingRepository,
    SqlModelRoomRepository,
)
from hotel.services.booking_service import BookingService
from hotel.services.room_service import RoomService


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_room_service(session: SessionDep) -> RoomService:
    return RoomService(
        rooms=SqlModelRoomRepository(session),
        new_id=lambda: str(uuid4()),
    )


def get_booking_service(session: SessionDep) -> BookingService:
    return BookingService(
        rooms=SqlModelRoomRepository(session),
        bookings=SqlModelBookingRepository(session),
        new_id=lambda: str(uuid4()),
    )


RoomServiceDep = Annotated[RoomService, Depends(get_room_service)]
BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
