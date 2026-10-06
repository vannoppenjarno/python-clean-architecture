"""Integration tests for the SQLModel repositories: real SQL and mapping against SQLite."""

from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import Session

from hotel.domain.booking import StayPeriod
from hotel.domain.room import Room
from hotel.infrastructure.sqlmodel_repositories import (
    SqlModelBookingRepository,
    SqlModelRoomRepository,
)
from tests.fakes import ROOM_101, make_booking

pytestmark = pytest.mark.integration


def test_room_round_trip_preserves_domain_object(session: Session) -> None:
    repo = SqlModelRoomRepository(session)

    repo.add(ROOM_101)

    assert repo.get("r1") == ROOM_101


def test_get_unknown_room_returns_none(session: Session) -> None:
    assert SqlModelRoomRepository(session).get("missing") is None


def test_list_all_returns_rooms_ordered_by_number(session: Session) -> None:
    repo = SqlModelRoomRepository(session)
    room_102 = Room(id="r2", number="102", capacity=4, nightly_rate=Decimal("180.00"))
    repo.add(room_102)
    repo.add(ROOM_101)

    assert repo.list_all() == [ROOM_101, room_102]


def test_find_overlapping_uses_half_open_ranges(session: Session) -> None:
    SqlModelRoomRepository(session).add(ROOM_101)
    repo = SqlModelBookingRepository(session)
    repo.add(make_booking("b1", StayPeriod(date(2025, 3, 1), date(2025, 3, 4))))

    assert repo.find_overlapping("r1", StayPeriod(date(2025, 3, 3), date(2025, 3, 5)))
    assert not repo.find_overlapping("r1", StayPeriod(date(2025, 3, 4), date(2025, 3, 6)))


def test_find_overlapping_ignores_other_rooms(session: Session) -> None:
    rooms = SqlModelRoomRepository(session)
    rooms.add(ROOM_101)
    room_102 = Room(id="r2", number="102", capacity=4, nightly_rate=Decimal("180.00"))
    rooms.add(room_102)
    repo = SqlModelBookingRepository(session)
    repo.add(make_booking("b1", StayPeriod(date(2025, 3, 1), date(2025, 3, 4)), room=room_102))

    assert repo.find_overlapping("r1", StayPeriod(date(2025, 3, 1), date(2025, 3, 4))) == []


def test_round_trip_preserves_domain_object(session: Session) -> None:
    SqlModelRoomRepository(session).add(ROOM_101)
    repo = SqlModelBookingRepository(session)
    booking = make_booking("b1", StayPeriod(date(2025, 3, 1), date(2025, 3, 4)))

    repo.add(booking)

    assert repo.get("b1") == booking


def test_remove_deletes_booking(session: Session) -> None:
    SqlModelRoomRepository(session).add(ROOM_101)
    repo = SqlModelBookingRepository(session)
    repo.add(make_booking("b1", StayPeriod(date(2025, 3, 1), date(2025, 3, 4))))

    repo.remove("b1")

    assert repo.get("b1") is None


def test_remove_unknown_booking_is_a_no_op(session: Session) -> None:
    SqlModelBookingRepository(session).remove("missing")
