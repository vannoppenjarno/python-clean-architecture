# Hotel API: Clean Architecture example

A small hotel booking service. Register rooms, book a room for a stay period, look up and cancel bookings. It shows:

- a **domain** in plain Python with real rules (`StayPeriod` invariants, half-open overlap, `Room.price_for`)
- **services** (use cases) that depend only on **ports** (`Protocol`s and an `IdFactory` alias)
- **SQLModel** tables and repository implementations confined to **infrastructure**, with explicit mapping to domain objects
- a **FastAPI** adapter with Pydantic schemas, domain error to HTTP mapping, and a single **composition root**
- unit tests with in-memory fakes, repository integration tests on SQLite, and API tests through `TestClient`

## Layer map

```
src/hotel/
  domain/          Room, StayPeriod, Booking, domain errors            (standard library only)
  repositories/    RoomRepository, BookingRepository                   (Protocols only)
  services/        RoomService, BookingService, commands, ports.py     (domain + ports)
  infrastructure/  Settings, engine, SQLModel tables, SqlModel*Repository
  api/             create_app, routers, schemas, errors, dependencies  (composition root)
```

Imports point inward only: `api -> infrastructure -> services -> repositories -> domain`. The domain and services import no FastAPI, Pydantic or SQLModel.

## Request flow

```
POST /bookings {room_id, guest_name, check_in, check_out}
  -> api/routers/bookings.py         Pydantic validates body; builds BookRoom command
  -> services/booking_service.py     BookingService.book_room(command)
      -> domain/booking.py           StayPeriod invariants, Room.price_for(period)
      -> repositories/bookings.py    BookingRepository.find_overlapping / add   (port)
          -> infrastructure/sqlmodel_repositories.py  SQL via SQLModel session  (impl)
  <- BookingOut.from_domain(booking) -> 201 JSON
  (RoomNotFound -> 404, RoomUnavailable -> 409, InvalidStayPeriod -> 422 via api/errors.py)
```

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| POST | `/rooms` | 201 | 422 invalid payload |
| GET | `/rooms` | 200 | |
| POST | `/bookings` | 201 | 404 unknown room, 409 overlap, 422 invalid payload or period |
| GET | `/bookings/{id}` | 200 | 404 |
| DELETE | `/bookings/{id}` | 204 | 404 |

## Run it

```bash
uv sync
uv run pytest                          # all tests
uv run pytest -m "not integration"     # skip the database tests
uv run fastapi dev src/hotel/api/app.py
```

The database URL comes from `HOTEL_DATABASE_URL` (default `sqlite:///./hotel.db`). Tables are created at startup for convenience; a production service would use migrations instead.

## Tests

```
tests/
  fakes.py         InMemoryRoomRepository, InMemoryBookingRepository, ROOM_101, make_booking
  conftest.py      shared fixtures
  unit/            domain and services, no database
  integration/     SQLModel repositories against in-memory SQLite (marked "integration")
  api/             HTTP contract via TestClient and create_app(Settings(database_url="sqlite://"))
```

`tests/` and its subfolders contain empty `__init__.py` files, so test modules import shared helpers as `from tests.fakes import ...`. Under pytest's default `prepend` import mode the project root is put on `sys.path`, so no `pythonpath` setting or `sys.path` hacks are needed. The application itself is imported as the installed `hotel` package (src layout).
