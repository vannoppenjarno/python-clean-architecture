"""Repository port for rooms, expressed in domain terms."""

from typing import Protocol

from hotel.domain.room import Room


class RoomRepository(Protocol):
    def add(self, room: Room) -> None: ...
    def get(self, room_id: str) -> Room | None: ...
    def list_all(self) -> list[Room]: ...
