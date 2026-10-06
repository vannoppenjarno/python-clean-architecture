"""Domain layer: the Room entity and its pricing rule."""

from dataclasses import dataclass
from decimal import Decimal

from hotel.domain.booking import StayPeriod


@dataclass(frozen=True)
class Room:
    id: str
    number: str
    capacity: int
    nightly_rate: Decimal

    def price_for(self, period: StayPeriod) -> Decimal:
        return self.nightly_rate * period.nights
