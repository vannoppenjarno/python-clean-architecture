"""Services layer: use cases for registering and listing rooms."""

from dataclasses import dataclass
from decimal import Decimal

from hotel.domain.room import Room
from hotel.repositories.rooms import RoomRepository
from hotel.services.ports import IdFactory


@dataclass(frozen=True)
class RegisterRoom:
    """Input command for the register-room use case."""

    number: str
    capacity: int
    nightly_rate: Decimal


class RoomService:
    def __init__(self, rooms: RoomRepository, new_id: IdFactory) -> None:
        self._rooms = rooms
        self._new_id = new_id

    def register_room(self, command: RegisterRoom) -> Room:
        room = Room(
            id=self._new_id(),
            number=command.number,
            capacity=command.capacity,
            nightly_rate=command.nightly_rate,
        )
        self._rooms.add(room)
        return room

    def list_rooms(self) -> list[Room]:
        return self._rooms.list_all()
