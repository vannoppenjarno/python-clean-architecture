# Layered Architecture Reference

How to apply Clean Architecture in a Python repository: domain at the core, services orchestrating use cases through ports, adapters and infrastructure at the edges. Code samples come from `examples/fastapi-hotel-api/`.

---

## 1. The Dependency Rule

```
┌──────────────────────────────────────────────────────────────┐
│ Infrastructure / frameworks / database                       │
│   SQLModel tables, engine/session, HTTP clients, settings    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Adapters / interfaces                                  │  │
│  │   FastAPI routers + schemas, CLI, repository impls     │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ Services / use cases                             │  │  │
│  │  │   orchestrate domain, depend on ports (Protocol) │  │  │
│  │  │  ┌────────────────────────────────────────────┐  │  │  │
│  │  │  │ Domain                                     │  │  │  │
│  │  │  │   entities, value objects, rules, errors   │  │  │  │
│  │  │  └────────────────────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
          source-code dependencies point inward only
```

**Rule:** a module may import from its own layer or any layer *inside* it, and never from a layer outside it. Control flow does go outward at runtime (a service calls a repository that hits the database). Dependency inversion makes that possible: the service calls a **port** it owns, and the outer layer supplies the implementation.

### Mapping to folders (normal application)

| Concept | Folder | Notes |
|---|---|---|
| Domain | `domain/` | Pure Python only |
| Services / use cases | `services/` | May also hold non-repository ports, for example `services/ports.py` with `Clock` or `Notifier` |
| Repository ports | `repositories/` | `Protocol`s only, with no implementations. They are inner-side contracts. |
| Infrastructure | `infrastructure/` | SQLModel tables, session/engine, repository implementations, API clients, settings |
| API adapter | `api/` | FastAPI app, routers, Pydantic schemas, dependency wiring (composition root) |

Folder names are a convention, not the point. A repository may use `adapters/` instead of `infrastructure/`, or `use_cases/` instead of `services/`. What matters is the direction of imports.

---

## 2. Domain

The domain expresses business concepts and rules in plain Python. It must be importable and testable with nothing installed except the standard library.

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

Domain rules:

- Use `@dataclass` (often `frozen=True`), `Enum` and small value objects. **Not** Pydantic models and **not** SQLModel tables.
- Validate invariants in the domain (`__post_init__`, factory functions). Pydantic validation at the API boundary does not replace domain invariants.
- Define domain exceptions (`RoomUnavailable`, `BookingNotFound`). They carry no HTTP meaning.
- Put behavior with the data it uses (Information Expert): `room.price_for(period)`, `period.overlaps(other)`.

> **Can the domain use Pydantic?** Avoid it by default. Pydantic belongs at boundaries. If a team deliberately accepts the dependency for a very small service, document that choice. Never let SQLModel tables become domain entities.

---

## 3. Ports (Repository and External-Service Interfaces)

Ports are `Protocol`s owned by the inner side. They describe what the use cases **need** in domain language.

```python
# repositories/bookings.py
from typing import Protocol

from hotel.domain.booking import Booking, StayPeriod


class BookingRepository(Protocol):
    def add(self, booking: Booking) -> None: ...
    def get(self, booking_id: str) -> Booking | None: ...
    def find_overlapping(self, room_id: str, period: StayPeriod) -> list[Booking]: ...
    def remove(self, booking_id: str) -> None: ...
```

### Domain-specific beats generic CRUD

```python
# AVOID as the default architecture
DataObject = dict[str, Any]

class DataInterface(Protocol):
    def read_by_id(self, id: str) -> DataObject: ...
    def read_all(self) -> list[DataObject]: ...
    def create(self, data: DataObject) -> DataObject: ...
```

Why to avoid it:

- **No types.** Typos in keys surface at runtime, and the IDE and type checker can't help.
- **Leaky queries.** Services end up calling `read_all()` and filtering in Python because the port can't express "overlapping bookings for room X".
- **Unclear intent.** The port shows *how* storage works, not *what* the use case needs.
- **Fakes that lie.** A dict-backed fake accepts any shape, so tests pass with data production would reject.

Guidelines:

- Name methods after the questions the use cases ask, such as `find_overlapping` or `get_by_email`.
- Accept and return **domain objects** or primitives, never ORM rows or dicts.
- Return `None` (or raise a domain exception) for "not found". Pick one convention per project.
- A small typed generic base (`class Repository[T](Protocol)`) is fine if many aggregates truly share identical needs. Treat it as a convenience, not the architecture.

### Other ports

External services follow the same rule:

```python
# services/ports.py
class PaymentGateway(Protocol):
    def charge(self, booking_id: str, amount: Decimal) -> PaymentReceipt: ...

Clock = Callable[[], datetime]
IdFactory = Callable[[], str]
```

Use a `Callable` alias when the dependency is a single behavior. Use a `Protocol` when it has several related methods.

---

## 4. Services (Use Cases)

Services implement application use cases: load what is needed through ports, apply domain rules, persist through ports.

```python
# services/booking_service.py
from dataclasses import dataclass

from hotel.domain.booking import Booking, StayPeriod
from hotel.domain.errors import RoomNotFound, RoomUnavailable
from hotel.repositories.bookings import BookingRepository
from hotel.repositories.rooms import RoomRepository
from hotel.services.ports import IdFactory


@dataclass(frozen=True)
class BookRoom:
    """Input command for the book-room use case."""
    room_id: str
    guest_name: str
    period: StayPeriod


class BookingService:
    def __init__(
        self,
        rooms: RoomRepository,
        bookings: BookingRepository,
        new_id: IdFactory,
    ) -> None:
        self._rooms = rooms
        self._bookings = bookings
        self._new_id = new_id

    def book_room(self, command: BookRoom) -> Booking:
        room = self._rooms.get(command.room_id)
        if room is None:
            raise RoomNotFound(command.room_id)
        if self._bookings.find_overlapping(room.id, command.period):
            raise RoomUnavailable(room.id, command.period)

        booking = Booking(
            id=self._new_id(),
            room_id=room.id,
            guest_name=command.guest_name,
            period=command.period,
            total_price=room.price_for(command.period),
        )
        self._bookings.add(booking)
        return booking
```

Service rules:

- Depend on ports (constructor injection). Never import from `infrastructure/` or `api/`.
- **No raw SQL, ORM queries, sessions or `select()`** in services.
- **No `HTTPException`** and no status codes. Raise domain exceptions.
- Accept typed inputs (a command dataclass or explicit parameters), not request schemas and not `dict[str, Any]`.
- Keep the service thin. If logic only concerns domain data, move it into the domain.
- A plain module of functions with dependencies passed as parameters is equally valid. Use a class when several use cases share the same dependencies.

---

## 5. Infrastructure (Persistence with SQLModel)

SQLModel tables are **persistence models**. They live in infrastructure and are mapped to and from domain objects inside the repository implementation.

```python
# infrastructure/tables.py
from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel


class BookingTable(SQLModel, table=True):
    __tablename__ = "bookings"

    id: str = Field(primary_key=True)
    room_id: str = Field(foreign_key="rooms.id", index=True)
    guest_name: str
    check_in: date
    check_out: date
    total_price: Decimal = Field(max_digits=10, decimal_places=2)
```

```python
# infrastructure/sqlmodel_repositories.py
from sqlmodel import Session, col, select

from hotel.domain.booking import Booking, StayPeriod
from hotel.infrastructure.tables import BookingTable


class SqlModelBookingRepository:
    """Implements repositories.bookings.BookingRepository (structurally)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, booking: Booking) -> None:
        self._session.add(_booking_to_row(booking))
        self._session.commit()

    def get(self, booking_id: str) -> Booking | None:
        row = self._session.get(BookingTable, booking_id)
        return _booking_to_domain(row) if row else None

    def find_overlapping(self, room_id: str, period: StayPeriod) -> list[Booking]:
        statement = select(BookingTable).where(
            BookingTable.room_id == room_id,
            col(BookingTable.check_in) < period.check_out,
            col(BookingTable.check_out) > period.check_in,
        )
        return [_booking_to_domain(row) for row in self._session.exec(statement)]

    def remove(self, booking_id: str) -> None:
        row = self._session.get(BookingTable, booking_id)
        if row is not None:
            self._session.delete(row)
            self._session.commit()


def _booking_to_domain(row: BookingTable) -> Booking:
    return Booking(
        id=row.id,
        room_id=row.room_id,
        guest_name=row.guest_name,
        period=StayPeriod(row.check_in, row.check_out),
        total_price=row.total_price,
    )


def _booking_to_row(booking: Booking) -> BookingTable:
    return BookingTable(
        id=booking.id,
        room_id=booking.room_id,
        guest_name=booking.guest_name,
        check_in=booking.period.check_in,
        check_out=booking.period.check_out,
        total_price=booking.total_price,
    )
```

Infrastructure rules:

- All SQL, queries, sessions, migrations and driver details live here.
- Queries are pushed into the database (`find_overlapping` filters in SQL), not done by loading everything into Python.
- Mapping functions are explicit and local to the repository implementation. Avoid magic `to_dict()` helpers that leak table shapes.
- **Transactions.** For one write per use case, committing inside the repository is fine. When a use case must make several writes atomically, introduce a Unit of Work that owns the session and commit (`patterns/unit-of-work.md`). Do not add it before you need it.
- External API clients follow the same shape: implement a port, map the external payload to domain types, and keep retries and timeouts here (`patterns/retry.md`, `patterns/adapter.md`).

### Settings

```python
# infrastructure/settings.py
@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./hotel.db"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(database_url=os.environ.get("HOTEL_DATABASE_URL", cls.database_url))
```

`pydantic-settings` is a good choice when there are many settings or validation needs. Read settings in the composition root and pass the values inward, never the whole settings object.

---

## 6. API Adapter (FastAPI)

FastAPI is an outer adapter. Routers translate HTTP into use-case calls and back. They hold no business rules.

### Schemas at the boundary (Pydantic v2)

```python
# api/schemas.py
from pydantic import BaseModel, ConfigDict, Field

from hotel.domain.booking import Booking


class BookingCreate(BaseModel):
    room_id: str
    guest_name: str = Field(min_length=1)
    check_in: date
    check_out: date


class BookingOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    room_id: str
    guest_name: str
    check_in: date
    check_out: date
    total_price: Decimal

    @classmethod
    def from_domain(cls, booking: Booking) -> "BookingOut":
        return cls(
            id=booking.id,
            room_id=booking.room_id,
            guest_name=booking.guest_name,
            check_in=booking.period.check_in,
            check_out=booking.period.check_out,
            total_price=booking.total_price,
        )
```

API schemas and domain objects are separate on purpose. The API contract can change (renamed fields, versioning) without touching the domain, and the domain can change without breaking clients.

### Router

```python
# api/routers/bookings.py
from hotel.api.dependencies import BookingServiceDep

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def book_room(body: BookingCreate, service: BookingServiceDep) -> BookingOut:
    command = BookRoom(
        room_id=body.room_id,
        guest_name=body.guest_name,
        period=StayPeriod(body.check_in, body.check_out),
    )
    return BookingOut.from_domain(service.book_room(command))
```

### Composition root (dependency wiring)

The only place that knows concrete classes:

```python
# api/dependencies.py
def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_booking_service(session: SessionDep) -> BookingService:
    return BookingService(
        rooms=SqlModelRoomRepository(session),
        bookings=SqlModelBookingRepository(session),
        new_id=lambda: str(uuid4()),
    )


BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
```

Tests can replace any provider with `app.dependency_overrides[get_booking_service] = ...`.

### Error mapping

Map domain exceptions to HTTP once, in the adapter:

```python
# api/errors.py
_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    RoomNotFound: 404,
    BookingNotFound: 404,
    RoomUnavailable: 409,
    InvalidStayPeriod: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    for error_type, status_code in _STATUS_BY_ERROR.items():
        app.add_exception_handler(error_type, _json_error(status_code))


def _json_error(status_code: int) -> Callable[[Request, Exception], JSONResponse]:
    def handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler
```

Services and the domain raise domain exceptions only. This table is the single place that knows about HTTP status codes.

### App factory

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = create_db_engine(settings.database_url)
        create_tables(app.state.engine)
        yield
        app.state.engine.dispose()

    app = FastAPI(title="Hotel API", lifespan=lifespan)
    app.include_router(rooms.router)
    app.include_router(bookings.router)
    register_error_handlers(app)
    return app
```

An app factory keeps tests isolated, because each test can build an app with its own database URL. In production, prefer migrations (Alembic) over `create_tables` at startup.

---

## 7. Request Flow, End to End

```
POST /bookings {room_id, guest_name, check_in, check_out}
  → api/routers/bookings.py         Pydantic validates body; builds BookRoom command
  → services/booking_service.py     BookingService.book_room(command)
      → domain/booking.py           StayPeriod invariants, Room.price_for(period)
      → repositories/bookings.py    BookingRepository.find_overlapping / add   (port)
          → infrastructure/sqlmodel_repositories.py  SQL via SQLModel session  (impl)
  ← BookingOut.from_domain(booking) → 201 JSON
  (RoomUnavailable → 409 via exception handler)
```

---

## 8. Scaling the Structure Down (and Up)

| Situation | Do this |
|---|---|
| Script | One module. Pure functions for logic and `main()` for I/O. No Protocols. |
| CLI / library, no DB | `src/<pkg>/` with `models.py`, `logic.py`, `cli.py`. Add a Protocol only where a test needs a fake (filesystem, HTTP). |
| Small service, 1–2 aggregates | You may merge `repositories/` into `services/ports.py` and keep `infrastructure/` as one or two modules. Keep the domain separate. |
| Normal service | Full layout (section 1). |
| Large system | One package per bounded context (`billing/`, `inventory/`), each with its own `domain/ services/ repositories/ infrastructure/`. A shared `api/` or per-context routers. |

Signals that you need **more** structure: services importing SQLModel, business rules in routers, tests needing a database to check a calculation, or a single `models.py` used as ORM table, API schema and domain object at once.

Signals that you have **too much**: folders with one trivial file, Protocols with exactly one implementation and no fake, pass-through services that only forward to a repository, or mapping code that is longer than the logic.

> A pass-through CRUD endpoint with no business rules does not need an elaborate use case. A thin service, or even a router calling a repository port directly, can be acceptable. Keep the port and keep SQL out of the router.

---

## 9. Adding a New Use Case: Checklist

1. **Domain:** add or extend entities, value objects and rules. Add domain exceptions. Unit-test them.
2. **Port:** add only the repository or external methods the use case needs, in domain terms.
3. **Service:** implement the use case against the ports. Unit-test it with in-memory fakes.
4. **Infrastructure:** implement the new port methods (SQLModel table and mapping). Integration-test them.
5. **API (if HTTP):** request/response schemas, router endpoint, error mapping, provider in `dependencies.py`. Add API tests.
6. **Wire:** include the router or register the CLI command in the composition root.

---

## 10. Production Readiness Checklist (HTTP services)

- [ ] Settings from environment, with no secrets in code
- [ ] Database migrations (Alembic) instead of `create_all` in production
- [ ] Domain exceptions mapped to consistent HTTP error responses
- [ ] Health endpoint (`GET /health`)
- [ ] Structured logging at the adapter and infrastructure boundaries
- [ ] CORS and rate limiting where public (`rest-api-design.md`)
- [ ] Tests: domain and service unit tests, repository integration tests, API tests
- [ ] `uv lock` committed. CI runs `uv sync --locked` and `uv run pytest`.
