"""Unit tests for the domain: plain objects, no fixtures, no frameworks."""

from datetime import date
from decimal import Decimal

import pytest

from hotel.domain.booking import StayPeriod
from hotel.domain.errors import InvalidStayPeriod, RoomUnavailable
from hotel.domain.room import Room


def test_price_is_nightly_rate_times_nights() -> None:
    room = Room(id="r1", number="101", capacity=2, nightly_rate=Decimal("120.00"))
    period = StayPeriod(date(2025, 3, 1), date(2025, 3, 4))

    assert room.price_for(period) == Decimal("360.00")


def test_nights_counts_days_between_check_in_and_check_out() -> None:
    assert StayPeriod(date(2025, 3, 1), date(2025, 3, 4)).nights == 3


@pytest.mark.parametrize(
    "check_out",
    [date(2025, 3, 4), date(2025, 3, 3)],
    ids=["same-day", "before-check-in"],
)
def test_period_must_end_after_it_starts(check_out: date) -> None:
    with pytest.raises(InvalidStayPeriod):
        StayPeriod(date(2025, 3, 4), check_out)


@pytest.mark.parametrize(
    ("other", "expected"),
    [
        (StayPeriod(date(2025, 3, 3), date(2025, 3, 5)), True),   # overlaps the end
        (StayPeriod(date(2025, 2, 27), date(2025, 3, 2)), True),  # overlaps the start
        (StayPeriod(date(2025, 3, 2), date(2025, 3, 3)), True),   # fully inside
        (StayPeriod(date(2025, 3, 4), date(2025, 3, 6)), False),  # starts on check-out day
        (StayPeriod(date(2025, 2, 27), date(2025, 3, 1)), False), # ends on check-in day
    ],
)
def test_overlap_is_half_open(other: StayPeriod, expected: bool) -> None:
    period = StayPeriod(date(2025, 3, 1), date(2025, 3, 4))
    assert period.overlaps(other) is expected


def test_room_unavailable_message_names_room_and_dates() -> None:
    error = RoomUnavailable("r1", StayPeriod(date(2025, 3, 1), date(2025, 3, 4)))

    assert str(error) == "Room 'r1' is already booked between 2025-03-01 and 2025-03-04"
