"""Domain layer: the StayPeriod value object and the Booking entity."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from hotel.domain.errors import InvalidStayPeriod


@dataclass(frozen=True)
class StayPeriod:
    """Value object: a half-open date range [check_in, check_out)."""

    check_in: date
    check_out: date

    def __post_init__(self) -> None:
        if self.check_out <= self.check_in:
            raise InvalidStayPeriod("check_out must be after check_in")

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    def overlaps(self, other: "StayPeriod") -> bool:
        return self.check_in < other.check_out and other.check_in < self.check_out


@dataclass(frozen=True)
class Booking:
    id: str
    room_id: str
    guest_name: str
    period: StayPeriod
    total_price: Decimal
