# Async Patterns

How to write async Python code for FastAPI applications. Covers coroutines, concurrent execution, async context managers, async generators, and the async database access patterns that FastAPI projects need.

> Content inspired by Arjan Codes' asyncio deep-dive examples.

---

## 1. Core Concepts

### Coroutines

A function defined with `async def` returns a coroutine. Calling it does not execute the body — you must `await` it.

```python
async def fetch_user(user_id: str) -> dict:
    # This runs when awaited, not when called
    return await db.read_by_id(user_id)
```

### The Event Loop

`asyncio.run()` creates an event loop and runs a coroutine to completion. FastAPI manages its own loop — you never call `asyncio.run()` inside a route handler.

```python
# Standalone script
async def main() -> None:
    result = await fetch_user("user-1")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

```python
# FastAPI route — no asyncio.run() needed
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    return await fetch_user(user_id)
```

### When to Use async def vs def in FastAPI

FastAPI handles both `async def` and plain `def` route handlers:

- **`async def`** — Use when the handler calls async I/O (database, HTTP client, file I/O). The handler runs on the main event loop.
- **`def`** — Use when the handler does only CPU-bound or synchronous work. FastAPI runs it in a thread pool automatically.

```python
# Async handler — awaits an async service (which awaits an async repository)
@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: str, service: AsyncBookingServiceDep) -> BookingOut:
    return BookingOut.from_domain(await service.get_booking(booking_id))

# Sync handler — CPU-bound computation
@router.post("/reports")
def generate_report(data: ReportRequest):
    return compute_report(data)  # synchronous, runs in thread pool
```

---

## 2. Concurrent Execution

### asyncio.gather()

Run multiple coroutines concurrently and collect all results. Use when you have independent I/O operations that don't depend on each other.

```python
import asyncio

async def fetch_user(user_id: str) -> dict: ...
async def fetch_orders(user_id: str) -> list[dict]: ...
async def fetch_preferences(user_id: str) -> dict: ...

async def get_user_dashboard(user_id: str) -> dict:
    # All three run concurrently — total time ≈ slowest call, not sum of all
    user, orders, prefs = await asyncio.gather(
        fetch_user(user_id),
        fetch_orders(user_id),
        fetch_preferences(user_id),
    )
    return {"user": user, "orders": orders, "preferences": prefs}
```

### asyncio.TaskGroup (Python 3.11+)

Structured concurrency — if any task fails, all others are cancelled. Preferred over `gather()` when you need all tasks to succeed.

```python
async def initialize_tables() -> None:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(create_table("users"))
        tg.create_task(create_table("orders"))
        tg.create_task(create_table("products"))
    # All tables created, or all cancelled if one failed
```

### When to Use Each

| Approach | Use when... |
|---|---|
| `await` sequentially | Results depend on each other (second call needs first result) |
| `asyncio.gather()` | Independent calls; partial success is acceptable |
| `asyncio.TaskGroup()` | Independent calls; all-or-nothing semantics needed |

---

## 3. Async Context Managers

### Writing Async Context Managers

The async version of `__enter__`/`__exit__` uses `__aenter__`/`__aexit__`:

```python
class AsyncDatabaseConnection:
    def __init__(self, url: str):
        self.url = url
        self.connection = None

    async def __aenter__(self):
        self.connection = await connect(self.url)
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.connection.close()
        return False

# Usage
async with AsyncDatabaseConnection("postgresql://...") as conn:
    result = await conn.execute("SELECT * FROM users")
```

### @asynccontextmanager Decorator

For simpler cases, use the decorator from `contextlib`:

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

@asynccontextmanager
async def transaction() -> AsyncGenerator[AsyncSession, None]:   # infrastructure helper
    session = AsyncSession(engine)
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### FastAPI Lifespan

FastAPI uses an async context manager for startup/shutdown logic:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, warm caches, open connections
    await create_tables()
    yield
    # Shutdown: close connections, flush buffers
    await close_database()

app = FastAPI(lifespan=lifespan)
```

---

## 4. Async Generators

Use `async def` with `yield` to create async iterators. Useful for streaming results or processing data in chunks.

```python
from typing import AsyncIterable

async def fetch_pages(url: str) -> AsyncIterable[dict]:
    page = 1
    while True:
        data = await http_get(f"{url}?page={page}")
        if not data["results"]:
            break
        yield data
        page += 1

# Consume with async for
async def process_all_pages(url: str) -> list[dict]:
    results = []
    async for page in fetch_pages(url):
        results.extend(page["results"])
    return results

# Async list comprehension
async def get_all_names(url: str) -> list[str]:
    return [item["name"] async for page in fetch_pages(url) for item in page["results"]]
```

---

## 5. Async Database Access

### SQLAlchemy AsyncSession

The standard pattern for async database access in FastAPI:

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

The engine and session factory belong in `infrastructure/`; the `get_session` provider lives in the composition root (`api/dependencies.py`).

Async does not change the architecture. Ports become `async` Protocols, services `await` them, and the SQL stays in infrastructure.

### Async Repository Port

A domain-specific port, defined on the inner side (`repositories/`), speaking in domain types:

```python
# repositories/bookings.py
from typing import Protocol

from hotel.domain.booking import Booking, StayPeriod
from hotel.domain.room import Room


class AsyncRoomRepository(Protocol):
    async def get(self, room_id: str) -> Room | None: ...


class AsyncBookingRepository(Protocol):
    async def add(self, booking: Booking) -> None: ...
    async def get(self, booking_id: str) -> Booking | None: ...
    async def find_overlapping(self, room_id: str, period: StayPeriod) -> list[Booking]: ...
```

### Async Service (Use Case)

```python
# services/booking_service.py
class AsyncBookingService:
    def __init__(
        self,
        rooms: AsyncRoomRepository,
        bookings: AsyncBookingRepository,
        new_id: Callable[[], str],
    ) -> None:
        self._rooms = rooms
        self._bookings = bookings
        self._new_id = new_id

    async def book_room(self, command: BookRoom) -> Booking:
        room = await self._rooms.get(command.room_id)
        if room is None:
            raise RoomNotFound(command.room_id)
        if await self._bookings.find_overlapping(room.id, command.period):
            raise RoomUnavailable(room.id, command.period)

        booking = Booking(
            id=self._new_id(),
            room_id=room.id,
            guest_name=command.guest_name,
            period=command.period,
            total_price=room.price_for(command.period),  # pure domain rule, no await
        )
        await self._bookings.add(booking)
        return booking
```

The service has no `AsyncSession`, no `select()` and no `HTTPException`. Domain logic (`price_for`, `overlaps`) stays synchronous.

### Async SQLModel Repository (Infrastructure)

```python
# infrastructure/async_repositories.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from hotel.domain.booking import Booking, StayPeriod
from hotel.infrastructure.tables import BookingTable


class AsyncSqlModelBookingRepository:
    """Implements AsyncBookingRepository (structurally)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, booking: Booking) -> None:
        self._session.add(_booking_to_row(booking))
        await self._session.commit()

    async def get(self, booking_id: str) -> Booking | None:
        row = await self._session.get(BookingTable, booking_id)
        return _booking_to_domain(row) if row else None

    async def find_overlapping(self, room_id: str, period: StayPeriod) -> list[Booking]:
        statement = select(BookingTable).where(
            BookingTable.room_id == room_id,
            col(BookingTable.check_in) < period.check_out,
            col(BookingTable.check_out) > period.check_in,
        )
        result = await self._session.execute(statement)
        return [_booking_to_domain(row) for row in result.scalars()]
```

`_booking_to_domain` / `_booking_to_row` are the same explicit mapping functions as in the sync repository (`layered-architecture.md`). SQLModel also offers `sqlmodel.ext.asyncio.session.AsyncSession` with an `exec()` method if you prefer that API.

Wire it in the composition root:

```python
# api/dependencies.py
AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_booking_service(session: AsyncSessionDep) -> AsyncBookingService:
    return AsyncBookingService(
        rooms=AsyncSqlModelRoomRepository(session),
        bookings=AsyncSqlModelBookingRepository(session),
        new_id=lambda: str(uuid4()),
    )
```

---

## 6. Testing Async Code

### Async In-Memory Fakes

Fakes implement the async ports with plain dicts. They live in `tests/fakes.py`, not in the production package.

```python
# tests/fakes.py
class AsyncInMemoryRoomRepository:
    def __init__(self, rooms: list[Room] | None = None) -> None:
        self._rooms = {room.id: room for room in rooms or []}

    async def get(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)


class AsyncInMemoryBookingRepository:
    def __init__(self) -> None:
        self.bookings: dict[str, Booking] = {}

    async def add(self, booking: Booking) -> None:
        self.bookings[booking.id] = booking

    async def get(self, booking_id: str) -> Booking | None:
        return self.bookings.get(booking_id)

    async def find_overlapping(self, room_id: str, period: StayPeriod) -> list[Booking]:
        return [
            b for b in self.bookings.values()
            if b.room_id == room_id and b.period.overlaps(period)
        ]
```

### Running async tests

Add an async test plugin to the dev dependency group: `uv add --dev pytest-asyncio` (or use the `anyio` pytest plugin that ships with AnyIO, which FastAPI already depends on, via `@pytest.mark.anyio`).

```python
# tests/unit/test_async_booking_service.py
import pytest


@pytest.mark.asyncio
async def test_book_room_computes_price() -> None:
    room = Room(id="r1", number="101", capacity=2, nightly_rate=Decimal("100.00"))
    bookings = AsyncInMemoryBookingRepository()
    service = AsyncBookingService(
        AsyncInMemoryRoomRepository([room]), bookings, new_id=lambda: "b1"
    )

    booking = await service.book_room(
        BookRoom("r1", "Ada", StayPeriod(date(2024, 1, 1), date(2024, 1, 4)))
    )

    assert booking.total_price == Decimal("300.00")
    assert await bookings.get("b1") == booking
```

Test the async SQLModel repository separately, as an integration test against an async engine (for example `sqlite+aiosqlite://`). See `testing-strategy.md`.

---

## 7. Common Mistakes

| Mistake | Problem | Fix |
|---|---|---|
| Calling `asyncio.run()` inside FastAPI | Creates nested event loop, crashes | Just `await` directly |
| Using `time.sleep()` in async code | Blocks the entire event loop | Use `await asyncio.sleep()` |
| Sequential awaits for independent calls | No concurrency benefit | Use `asyncio.gather()` |
| Mixing sync DB driver with async handler | Blocks event loop during queries | Use async driver (`asyncpg`, `aiosqlite`) |
| Forgetting `await` on a coroutine | Returns coroutine object instead of result | Always `await` async calls |
| Using sync file I/O in async code | Blocks event loop | Use `aiofiles` or run in executor |

---

## 8. Scaling FastAPI with Multiple Workers

A single FastAPI process runs one event loop on one CPU core. To use all cores, run multiple worker processes behind a process manager.

### Gunicorn + Uvicorn Workers

```bash
# Run 4 worker processes, each with its own event loop
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Rule of thumb:** Set workers to `2 * CPU_cores + 1`. For a 4-core machine: 9 workers.

### When to Scale Workers vs Async

| Bottleneck | Solution |
|---|---|
| I/O-bound (database, HTTP calls) | Use `async def` + `await` — one worker handles many concurrent requests |
| CPU-bound (data processing, ML inference) | Add more Gunicorn workers — each runs on a separate core |
| Both | Combine: multiple workers with async handlers |

### Docker Deployment

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

# Install dependencies first (cached layer), from the lockfile only
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Then the project itself
COPY src ./src
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "hotel.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Pin the uv image tag in real projects. To run several workers in one container, add `--workers 4` to `uvicorn` (or use Gunicorn with `uvicorn.workers.UvicornWorker` after `uv add gunicorn`).

For Kubernetes or similar orchestrators, prefer running a single Uvicorn worker per container and letting the orchestrator handle scaling (one process per pod is simpler to monitor and restart).
