"""API adapter layer: room endpoints. No business rules, only translation."""

from fastapi import APIRouter, status

from hotel.api.dependencies import RoomServiceDep
from hotel.api.schemas import RoomCreate, RoomOut
from hotel.services.room_service import RegisterRoom

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def register_room(body: RoomCreate, service: RoomServiceDep) -> RoomOut:
    command = RegisterRoom(
        number=body.number,
        capacity=body.capacity,
        nightly_rate=body.nightly_rate,
    )
    return RoomOut.from_domain(service.register_room(command))


@router.get("", response_model=list[RoomOut])
def list_rooms(service: RoomServiceDep) -> list[RoomOut]:
    return [RoomOut.from_domain(room) for room in service.list_rooms()]
