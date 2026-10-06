# Testing Strategy Reference

What to test at each layer, and how the architecture makes that cheap. Examples come from `examples/fastapi-hotel-api/`.

## Core Principle

Because the domain is pure Python and services depend on **ports**, almost all business behavior can be tested in milliseconds without a database, a web server or a mocking library. Slower tests are reserved for the code that actually touches infrastructure.

| Layer | Test type | Dependencies in the test | Location |
|---|---|---|---|
| Domain | Unit | None | `tests/unit/` |
| Services | Unit | In-memory **fakes** implementing the port Protocols | `tests/unit/` |
| Repository implementations | Integration | Real engine (SQLite in-memory, or a containerized DB that matches production) | `tests/integration/` |
| API adapter | API / integration | `TestClient`, app factory, test DB or overridden services | `tests/api/` |

Aim for many fast unit tests, fewer integration tests, and a handful of API tests per endpoint that cover the happy path, validation and error mapping.

---

## 1. Domain Unit Tests

No fixtures, no frameworks. Construct objects and assert behavior.

```python
from datetime import date
from decimal import Decimal

import pytest

from hotel.domain.booking import StayPeriod
from hotel.domain.errors import InvalidStayPeriod
from hotel.domain.room import Room


def test_price_is_nightly_rate_times_nights() -> None:
    room = Room(id="r1", number="101", capacity=2, nightly_rate=Decimal("120.00"))
    period = StayPeriod(date(2025, 3, 1), date(2025, 3, 4))

    assert room.price_for(period) == Decimal("360.00")


def test_period_must_end_after_it_starts() -> None:
    with pytest.raises(InvalidStayPeriod):
        StayPeriod(date(2025, 3, 4), date(2025, 3, 4))


@pytest.mark.parametrize(
    ("other", "expected"),
    [
        (StayPeriod(date(2025, 3, 3), date(2025, 3, 5)), True),   # overlaps the end
        (StayPeriod(date(2025, 3, 4), date(2025, 3, 6)), False),  # starts on check-out day
        (StayPeriod(date(2025, 2, 27), date(2025, 3, 1)), False), # ends on check-in day
    ],
)
def test_overlap_is_half_open(other: StayPeriod, expected: bool) -> None:
    period = StayPeriod(date(2025, 3, 1), date(2025, 3, 4))
    assert period.overlaps(other) is expected
```

---

## 2. Service Unit Tests with Fakes

A **fake** is a small, working, in-memory implementation of a port. It satisfies the `Protocol` structurally, with no inheritance needed.

```python
# tests/fakes.py
ROOM_101 = Room(id="r1", number="101", capacity=2, nightly_rate=Decimal("120.00"))


def make_booking(booking_id: str, period: StayPeriod, room: Room = ROOM_101) -> Booking:
    return Booking(booking_id, room.id, "Ada", period, room.price_for(period))


class InMemoryRoomRepository:
    def __init__(self, rooms: list[Room] | None = None) -> None:
        self._rooms = {room.id: room for room in rooms or []}

    def add(self, room: Room) -> None:
        self._rooms[room.id] = room

    def get(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def list_all(self) -> list[Room]:
        return list(self._rooms.values())


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self.bookings: dict[str, Booking] = {}

    def add(self, booking: Booking) -> None:
        self.bookings[booking.id] = booking

    def get(self, booking_id: str) -> Booking | None:
        return self.bookings.get(booking_id)

    def find_overlapping(self, room_id: str, period: StayPeriod) -> list[Booking]:
        return [
            b for b in self.bookings.values()
            if b.room_id == room_id and b.period.overlaps(period)
        ]

    def remove(self, booking_id: str) -> None:
        self.bookings.pop(booking_id, None)
```

```python
# tests/unit/test_booking_service.py
def make_service(*rooms: Room) -> tuple[BookingService, InMemoryBookingRepository]:
    bookings = InMemoryBookingRepository()
    ids = iter(f"b{n}" for n in range(1, 100))
    service = BookingService(InMemoryRoomRepository(list(rooms)), bookings, new_id=lambda: next(ids))
    return service, bookings


def test_book_room_stores_priced_booking() -> None:
    service, bookings = make_service(ROOM_101)

    booking = service.book_room(BookRoom("r1", "Ada", StayPeriod(date(2025, 3, 1), date(2025, 3, 3))))

    assert booking.id == "b1"
    assert booking.total_price == Decimal("240.00")
    assert bookings.get("b1") == booking


def test_book_room_rejects_overlap() -> None:
    service, _ = make_service(ROOM_101)
    service.book_room(BookRoom("r1", "Ada", StayPeriod(date(2025, 3, 1), date(2025, 3, 3))))

    with pytest.raises(RoomUnavailable):
        service.book_room(BookRoom("r1", "Bob", StayPeriod(date(2025, 3, 2), date(2025, 3, 5))))
```

### Fakes vs mocks

- **Prefer fakes.** They have real behavior, make tests read like specifications, and survive refactoring of call order.
- Use `unittest.mock` sparingly: to assert that an outbound side effect happened (an email sent, an event published), or to simulate a failure that a fake can't easily produce.
- Keep fakes in `tests/` (`tests/fakes.py` or `conftest.py`), not in production packages.
- A fake must honor the port's contract, for example the same "not found" convention. If the fake and the real implementation drift apart, the integration tests (section 3) will catch it. Consider running one shared contract test suite against both.

### Simulating failures

```python
class FailingBookingRepository(InMemoryBookingRepository):
    def add(self, booking: Booking) -> None:
        raise ConnectionError("database unavailable")
```

Subclassing a *test fake* for one scenario is fine. Composition-over-inheritance concerns apply to production design, not to throwaway test doubles.

---

## 3. Repository Integration Tests

Repository implementations contain real SQL and mapping, so test them against a real engine.

```python
# tests/integration/conftest.py
from collections.abc import Iterator

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import hotel.infrastructure.tables  # noqa: F401  (registers the tables on SQLModel.metadata)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()
```

```python
# tests/integration/test_sqlmodel_repositories.py
def test_find_overlapping_uses_half_open_ranges(session: Session) -> None:
    SqlModelRoomRepository(session).add(ROOM_101)
    repo = SqlModelBookingRepository(session)
    repo.add(make_booking("b1", StayPeriod(date(2025, 3, 1), date(2025, 3, 4))))

    assert repo.find_overlapping("r1", StayPeriod(date(2025, 3, 3), date(2025, 3, 5)))
    assert not repo.find_overlapping("r1", StayPeriod(date(2025, 3, 4), date(2025, 3, 6)))


def test_round_trip_preserves_domain_object(session: Session) -> None:
    SqlModelRoomRepository(session).add(ROOM_101)
    repo = SqlModelBookingRepository(session)
    booking = make_booking("b1", StayPeriod(date(2025, 3, 1), date(2025, 3, 4)))

    repo.add(booking)

    assert repo.get("b1") == booking
```

- SQLite in-memory is fast and good for mapping and query logic. If the code relies on database-specific behavior (Postgres types, locking, JSONB), run the integration suite against that database, for example with `testcontainers`.
- Mark slow suites (`@pytest.mark.integration`) so developers can run `uv run pytest -m "not integration"` locally.

---

## 4. API Tests

Test the HTTP contract: status codes, response shapes, validation and error mapping. Don't re-test business rules exhaustively here.

```python
# tests/api/conftest.py
@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(Settings(database_url="sqlite://"))
    with TestClient(app) as client:   # runs lifespan → creates tables
        yield client
```

```python
# tests/api/test_bookings_api.py
def test_double_booking_returns_409(client: TestClient) -> None:
    room = client.post("/rooms", json={"number": "101", "capacity": 2, "nightly_rate": "100.00"}).json()
    body = {"room_id": room["id"], "guest_name": "Ada", "check_in": "2025-03-01", "check_out": "2025-03-03"}

    assert client.post("/bookings", json=body).status_code == 201
    assert client.post("/bookings", json=body).status_code == 409


def test_invalid_payload_returns_422(client: TestClient) -> None:
    assert client.post("/bookings", json={"room_id": "x"}).status_code == 422
```

To test an endpoint in isolation from the database, override the service provider:

```python
app.dependency_overrides[get_booking_service] = lambda: BookingService(
    InMemoryRoomRepository([ROOM_101]), InMemoryBookingRepository(), new_id=lambda: "b1"
)
```

> With an in-memory SQLite URL, every new connection gets an empty database. The example's `create_db_engine` uses `StaticPool` for `sqlite://` so all sessions share one connection.

---

## 5. General Practices

### Arrange, act, assert

Keep the three phases visually distinct. One behavior per test.

### Naming

Name the scenario and the expectation: `test_book_room_rejects_overlap`, `test_overlap_is_half_open`, `test_double_booking_returns_409`.

### Edge cases to check systematically

| Category | Examples |
|---|---|
| Empty / zero | No rooms, zero-night period |
| Boundaries | Period ending exactly on another's start |
| Invalid | Negative rate, `check_out <= check_in`, missing fields (API) |
| Duplicates / conflicts | Same booking twice, duplicate room number |
| Not found | Unknown room / booking id |

### Parametrize instead of copy-paste

Use `@pytest.mark.parametrize` for input/output tables.

### Isolation

Never share mutable state between tests. Build fakes or sessions per test, or in function-scoped fixtures.

### Determinism: inject time, IDs and randomness

```python
# BAD: depends on the wall clock
def is_arriving_today(booking: Booking) -> bool:
    return booking.period.check_in == date.today()

# GOOD: inject "today"
def is_arriving_today(booking: Booking, today: date) -> bool:
    return booking.period.check_in == today
```

The same applies to `uuid4()`, which is why `BookingService` receives `new_id`, and to `random`.

### Skip and xfail

- `@pytest.mark.skip(reason=...)` always skips.
- `@pytest.mark.skipif(cond, reason=...)` skips conditionally, for example by platform or missing service.
- `@pytest.mark.xfail(reason=...)` marks a known bug. An unexpected pass shows up as `XPASS`.

---

## 6. Refactoring Legacy Code Toward Testability

1. **Find the hard dependency.** Look for a session, client or `datetime.now()` created inside the function.
2. **Pass it in.** Make it a parameter or constructor argument.
3. **Introduce a port.** Define a domain-specific `Protocol` for what the code actually uses.
4. **Test with a fake.** Write the unit test against the fake, and move the real implementation to infrastructure with its own integration test.

```python
# BEFORE: SQL inside business logic, untestable without a DB
def book(room_id: str, period: StayPeriod) -> Booking:
    with Session(engine) as s:
        clash = s.exec(select(BookingTable).where(...)).first()
        ...

# AFTER: service depends on a port; SQL lives in SqlModelBookingRepository
class BookingService:
    def __init__(self, rooms: RoomRepository, bookings: BookingRepository, new_id: IdFactory) -> None: ...
```

---

## 7. Running Tests

```bash
uv run pytest                       # everything
uv run pytest tests/unit            # fast feedback
uv run pytest -m "not integration"  # skip slow suites
uv run pytest --cov=src/<package>   # with pytest-cov in the dev group
```

See `testing-advanced.md` for fixture organization, property-based testing (Hypothesis), stateful testing and coverage philosophy.
