# Domain Modeling Reference

How to model the core of an application: the business concepts, their rules and their behavior, in plain Python and independent of frameworks and infrastructure. Examples come from `examples/fastapi-hotel-api/src/hotel/domain/`.

> Partly inspired by Arjan Codes' teaching on domain models and DDD; adapted to this standard. For the strategic side (ubiquitous language, bounded contexts), see `domain-driven-design.md`.

---

## 1. What the Domain Model Is

The domain model is the code representation of the problem you're solving. It captures:

- **Entities**: things with an identity that persists while their attributes change (`Room`, `Booking`).
- **Value objects**: things defined only by their values, usually immutable (`StayPeriod`, `Money`, `EmailAddress`).
- **Rules and invariants**: what must always be true (a stay ends after it starts) and how values are derived (price = nightly rate × nights).
- **Domain errors**: named violations of those rules (`RoomUnavailable`, `InvalidStayPeriod`).

It sits at the **center** of the architecture. Every other layer may depend on it, and it depends on none of them:

```
api/ ──► services/ ──► domain/ ◄── repositories/ (ports) ◄── infrastructure/
```

**Key insight:** the model is what lasts. Frameworks, databases and API shapes change around it. Keeping the domain free of them is what makes those changes cheap.

---

## 2. Start with the Data

Before writing routers, tables or services, sketch the domain types and the rules between them. Starting from the data usually gives a cleaner design than starting from endpoints or tables.

1. List the nouns of the problem. Decide which have identity (entities) and which are just values (value objects).
2. Write each as a `@dataclass` with precise types.
3. Add the rules as methods or `__post_init__` checks on the type that owns the data.
4. Write unit tests for those rules. They need nothing but pytest.
5. Only then design the ports, services and adapters around the model.

```python
# domain/booking.py
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
```

```python
# domain/room.py
@dataclass(frozen=True)
class Room:
    id: str
    number: str
    capacity: int
    nightly_rate: Decimal

    def price_for(self, period: StayPeriod) -> Decimal:
        return self.nightly_rate * period.nights
```

---

## 3. Which Python Constructs to Use

| Concept | Use | Avoid in the domain |
|---|---|---|
| Entity | `@dataclass` (frozen when practical; replace instead of mutate) | Pydantic `BaseModel`, SQLModel `table=True`, ORM classes |
| Value object | `@dataclass(frozen=True)` with validation in `__post_init__` | Bare `str`/`float`/`dict` for meaningful concepts |
| Fixed set of options | `Enum` / `StrEnum` | Magic strings |
| Money | `Decimal` (or a `Money` value object with currency) | `float` |
| Rule touching one object | Method or property on that object | Free function that pulls the object apart |
| Rule spanning several objects, no I/O | Pure function in `domain/` (a domain service) | Putting it in an application service |
| Rule violation | Subclass of a `DomainError` base exception | `HTTPException`, status codes, `ValueError` everywhere |

### Why not Pydantic or SQLModel in the domain?

- **Pydantic** validates and serializes data crossing a boundary. Using it for entities couples the core to a library, mixes the API contract with the business model, and usually invites `dict`-shaped thinking. Use Pydantic schemas in `api/` and map them to domain objects (`pydantic-validation.md` §7).
- **SQLModel** tables describe how data is *stored*. If they double as entities, persistence concerns (nullable ids, foreign-key columns, lazy relationships, sessions) leak into the business rules. Keep tables in `infrastructure/` and map them explicitly in the repository implementation (`layered-architecture.md` §5).

Separate types may look alike at first. They stop looking alike as soon as the API, the schema or the rules evolve, and then the separation pays for itself.

---

## 4. Value Objects: Make Illegal States Unrepresentable

Wrap a primitive in a value object when the concept carries rules or would otherwise be validated in many places:

```python
@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        if "@" not in self.value:
            raise InvalidEmail(self.value)
```

Once a `StayPeriod` exists, it is valid. No code downstream has to recheck `check_out > check_in`.

Use them where they earn their place (KISS). A plain `str` for a guest name is fine. A dedicated type for every field is ceremony. More techniques: `patterns/value-objects.md`.

---

## 5. Put Behavior with the Data (Avoid the Anemic Model)

If services keep pulling fields out of an object to compute something, the logic belongs on the object (Information Expert, "Tell, Don't Ask"):

```python
# Ask: the service does the domain's job
total = room.nightly_rate * (period.check_out - period.check_in).days

# Tell: the domain owns the rule
total = room.price_for(period)
```

The split of responsibilities:

| Lives in the domain | Lives in services (use cases) |
|---|---|
| Invariants, calculations, state transitions, overlap rules | Loading and saving through ports |
| Domain errors | Choosing which domain operations to run, and in what order |
| Pure decisions on data already in memory | Transactions, calling external services, publishing events |

A service like `BookingService.book_room` should read as a short script: load the room, check availability through the port, ask the domain for the price, store the booking. If it contains arithmetic or business conditionals about a single object, move them into the domain.

That said, not every project has rich rules. For plain CRUD data, a dataclass with no methods is fine. Don't invent behavior to avoid being "anemic" (YAGNI).

---

## 6. Keep the Domain Pure

The domain does no I/O and knows nothing of its environment:

- **No** database sessions, HTTP calls, file access, environment variables or logging configuration.
- **No** imports from `fastapi`, `pydantic`, `sqlmodel`, `sqlalchemy` or your own `services`, `infrastructure` or `api` packages.
- **No hidden inputs.** Don't call `datetime.now()`, `uuid4()` or `random` inside domain logic. Pass them in as values (`today: date`), or let the service supply them through a port (`IdFactory`).

```python
# BAD: hidden dependency on the clock
def is_arriving_today(booking: Booking) -> bool:
    return booking.period.check_in == date.today()

# GOOD: the caller provides "today"
def is_arriving_today(booking: Booking, today: date) -> bool:
    return booking.period.check_in == today
```

This purity is what makes domain tests trivial (`testing-strategy.md` §1). It can be enforced with an import-linter "forbidden" contract (`project-setup.md` §5).

---

## 7. Identity and Relationships

- **IDs.** Generate them in the service through an injected `IdFactory` (UUID strings by default), not as database autoincrement values. The domain object is then complete before it is saved, and tests stay deterministic.
- **References between aggregates by ID.** A `Booking` holds `room_id`, not a `Room` object loaded by an ORM relationship. The service loads what it needs through ports. This avoids lazy loading leaking into the domain and keeps each aggregate independently storable.
- **Aggregates.** Group objects that must stay consistent together (an `Order` with its `OrderLine`s) and change them only through the root. Repositories exist per aggregate root, not per table.

---

## 8. Mapping at the Boundaries

The domain is translated at each edge, never shared directly:

```
JSON ──Pydantic schema──► command / domain object ──► service ──► domain
                                                          │
domain object ◄──mapping functions──► SQLModel table ◄────┘ (in the repository implementation)
```

- **API side** (`api/schemas.py`): `BookingCreate` is validated by Pydantic and converted into a `BookRoom` command with a `StayPeriod`. The result is converted back with `BookingOut.from_domain(booking)`.
- **Persistence side** (`infrastructure/sqlmodel_repositories.py`): private functions such as `_booking_to_row` and `_booking_to_domain` translate between `BookingTable` and `Booking`.
- `dict[str, Any]` is acceptable only for raw input before validation. Once data is inside, it is typed.

---

## 9. Modeling Smells

| Smell | Fix |
|---|---|
| Prefixed fields (`customer_name`, `customer_email`) | Extract a `Customer` type |
| Parallel lists or dicts keyed by the same id | Extract a dataclass per item |
| The same validation repeated in several places | Introduce a value object |
| `if booking.status == "cancelled"` strings | Use an `Enum` |
| Entity imports a session, client or settings | Move the I/O to a port and an infrastructure implementation |
| One class used as ORM table, API schema and entity | Split into three types with explicit mapping |
| Services full of calculations on one object's fields | Move the rule onto that object |
| Deep inheritance between entities | Prefer composition, for example a `pricing: PricingPolicy` field or a `Callable` |

---

## 10. Checklist

- [ ] Domain types are dataclasses or enums with precise types (no `dict[str, Any]`, no `float` money)
- [ ] Invariants are enforced when objects are created
- [ ] Rules sit on the type that owns the data, and services only orchestrate
- [ ] Domain errors are specific and carry no HTTP or database meaning
- [ ] No framework, ORM, Pydantic or I/O imports in `domain/`
- [ ] Time, IDs and randomness are passed in, not fetched
- [ ] Mapping to API schemas and tables happens in `api/` and `infrastructure/`
- [ ] Every rule has a fast unit test with no fixtures beyond plain objects
- [ ] Modeling depth matches the problem: no value objects or aggregates without a reason
