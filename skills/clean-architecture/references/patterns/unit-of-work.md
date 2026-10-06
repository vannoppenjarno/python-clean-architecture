# Unit of Work

Group multiple database operations into a single transaction that succeeds or fails atomically. Uses Python's context manager protocol to automatically commit on success and rollback on exception.

---

## The Problem

Multiple related writes must either all succeed or all fail. Without transaction management, a failure midway leaves data in an inconsistent state:

```python
# Dangerous: if add("Banana") fails, "Apple" is already committed
repo.add("Apple", 10)
repo.add("Banana", 20)    # exception here!
repo.add("Cherry", 30)    # never runs
# Database now has Apple but not Banana or Cherry
```

---

## Basic Unit of Work

Track new, modified, and removed objects, then commit them all at once:

```python
from dataclasses import dataclass, field


@dataclass
class User:
    username: str


@dataclass
class UnitOfWork:
    new_users: list[User] = field(default_factory=list)
    dirty_users: list[User] = field(default_factory=list)
    removed_users: list[User] = field(default_factory=list)

    def register_new(self, user: User) -> None:
        self.new_users.append(user)

    def register_dirty(self, user: User) -> None:
        if user not in self.dirty_users:
            self.dirty_users.append(user)

    def register_removed(self, user: User) -> None:
        self.removed_users.append(user)

    def commit(self) -> None:
        for obj in self.new_users:
            print(f"Inserting {obj}")
        for obj in self.dirty_users:
            print(f"Updating {obj}")
        for obj in self.removed_users:
            print(f"Deleting {obj}")
        self.new_users.clear()
        self.dirty_users.clear()
        self.removed_users.clear()
```

This is the conceptual pattern. In practice, the database driver handles tracking.

---

## Context Manager Unit of Work

The Pythonic implementation uses `__enter__`/`__exit__` for automatic transaction lifecycle:

```python
import sqlite3


class Repository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def add(self, name: str, quantity: int) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO items (name, quantity) VALUES (?, ?)", (name, quantity)
        )

    def all(self) -> list[dict]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM items")
        return [dict(row) for row in cursor.fetchall()]


class UnitOfWork:
    def __init__(self, db_name: str = "example.db"):
        self.db_name = db_name
        self.connection: sqlite3.Connection | None = None
        self.repository: Repository | None = None

    def __enter__(self) -> "UnitOfWork":
        self.connection = sqlite3.connect(self.db_name)
        self.connection.execute("BEGIN")
        self.connection.row_factory = sqlite3.Row
        self.repository = Repository(self.connection)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_val:
            self.connection.rollback()   # exception → undo everything
        else:
            self.connection.commit()     # clean exit → save everything
        self.connection.close()
```

Usage — all operations within the `with` block are atomic:

```python
try:
    with UnitOfWork() as uow:
        uow.repository.add("Apple", 10)
        uow.repository.add("Banana", 20)
        # If an exception occurs here, both inserts are rolled back
except Exception as e:
    logging.error(f"Transaction failed: {e}")
```

---

## SQLAlchemy / SQLModel Unit of Work

SQLAlchemy's `Session` (and SQLModel's, which builds on it) already implements Unit of Work internally: it tracks changes and flushes them in one transaction. Wrapping it in a context manager gives a clean transaction boundary:

```python
import contextlib
from sqlmodel import Session


@contextlib.contextmanager
def transaction(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
```

This is fine inside infrastructure code. Services, however, must not see a `Session`, so in the layered architecture the Unit of Work is split into a port and an implementation.

---

## Unit of Work in the Layered Architecture

> **Don't introduce it until you need it.** If each use case performs one write, letting the repository commit (as `SqlModelBookingRepository.add` does in `references/layered-architecture.md`) is simpler. Add a Unit of Work when a use case must make **several writes atomically**.

### The port (inner side)

A `Protocol` that exposes the typed repositories plus `commit` / `rollback`, and works as a context manager:

```python
# services/ports.py (or repositories/unit_of_work.py)
from typing import Protocol, Self

from hotel.repositories.bookings import BookingRepository
from hotel.repositories.rooms import RoomRepository


class UnitOfWork(Protocol):
    rooms: RoomRepository
    bookings: BookingRepository

    def __enter__(self) -> Self: ...
    def __exit__(self, *exc: object) -> None: ...   # rolls back if commit() wasn't called
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

### The service (use case)

The service decides *what* belongs in one transaction, without knowing *how* transactions work:

```python
# services/booking_service.py
class GroupBookingService:
    def __init__(self, uow: UnitOfWork, new_id: Callable[[], str]) -> None:
        self._uow = uow
        self._new_id = new_id

    def book_group(self, commands: list[BookRoom]) -> list[Booking]:
        with self._uow as uow:
            bookings = []
            for command in commands:
                room = uow.rooms.get(command.room_id)
                if room is None:
                    raise RoomNotFound(command.room_id)
                if uow.bookings.find_overlapping(room.id, command.period):
                    raise RoomUnavailable(room.id, command.period)   # nothing is committed
                booking = Booking(self._new_id(), room.id, command.guest_name,
                                  command.period, room.price_for(command.period))
                uow.bookings.add(booking)
                bookings.append(booking)
            uow.commit()                                             # all or nothing
            return bookings
```

### The implementation (infrastructure/)

The SQLModel Unit of Work owns the session and builds the repositories on it. Repositories used through a Unit of Work only `add`/`flush`; they never commit themselves. Here that is an `autocommit` flag on the repository implementation; once every use case goes through a Unit of Work, drop the commit from the repositories entirely.

```python
# infrastructure/unit_of_work.py
class SqlModelUnitOfWork:
    """Implements UnitOfWork (structurally)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __enter__(self) -> "SqlModelUnitOfWork":
        self._session = Session(self._engine)
        self.rooms = SqlModelRoomRepository(self._session, autocommit=False)
        self.bookings = SqlModelBookingRepository(self._session, autocommit=False)
        return self

    def __exit__(self, *exc: object) -> None:
        self.rollback()          # no-op after a successful commit
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
```

### Wiring and testing

```
api/dependencies.py (composition root)
  └── creates SqlModelUnitOfWork(engine)
        └── passes it to GroupBookingService (typed as the UnitOfWork port)
              └── service uses uow.rooms / uow.bookings and calls uow.commit()
```

In unit tests, pass a `FakeUnitOfWork` that holds the in-memory repositories from `tests/fakes.py` and records `committed = True` in `commit()`. Then assert both the stored data and whether a commit happened (for example, that a failed group booking never committed).

---

## When to Use

| Use Unit of Work when... | Skip when... |
|---|---|
| Multiple entities must be written atomically | Single-entity CRUD operations |
| Business rule requires all-or-nothing semantics | Database driver handles transactions implicitly |
| You need explicit control over commit/rollback | Simple operations with auto-commit |
| A use case writes through multiple repositories | One repository write per use case |

---

## Trade-offs

| Advantage | Cost |
|---|---|
| Atomic transactions — consistent data | Slightly more ceremony than auto-commit |
| Automatic rollback on exceptions | Must ensure all writes go through the UoW |
| Clean boundary between business logic and persistence | Not needed for simple single-write operations |
| Context manager makes the boundary explicit | Connection lifetime tied to `with` block scope |
