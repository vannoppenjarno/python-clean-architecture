# Repository Pattern

**Recognize:** Data access logic (SQL queries, file I/O, API calls) is mixed into domain classes or scattered across the codebase. Changing the storage backend requires modifying business logic.

**Problem:** Tight coupling between data representation and data storage makes code hard to test, hard to extend, and impossible to swap storage backends without rewriting business logic.

> Content inspired by Arjan Codes' deep dive into the Repository pattern.

---

## Core Idea

The Repository pattern separates **how you store data** from **how you access data**. A repository provides a collection-like interface (get, add, update, delete) that hides the storage mechanism behind it.

```
Services / use cases
    │  depend on
    ▼
Repository port (Protocol)         ← defined on the inner side (repositories/), domain-specific
    ▲  implemented by
    │
    ├── SqlModelRepository         ← infrastructure/
    ├── FileRepository             ← infrastructure/
    └── InMemoryRepository         ← tests/fakes.py
```

The arrow from the implementation points *inward* to the port. This is dependency inversion: infrastructure depends on the contract the use cases defined, not the other way round.

---

## Before: Coupled Data + Storage

```python
@dataclass
class Post:
    id: str
    title: str
    content: str

    @classmethod
    def get_by_id(cls, post_id: str, db_path: str) -> "Post":
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        conn.close()
        return Post(id=row[0], title=row[1], content=row[2])

    @classmethod
    def add(cls, post: "Post", db_path: str) -> None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO posts VALUES (?, ?, ?)",
                       (post.id, post.title, post.content))
        conn.commit()
        conn.close()
```

*(Before-state simplified: `Post` without `published_on`.)*

Problems:
- `Post` knows about SQLite, connection strings, SQL syntax
- Can't test without a real database
- Switching to NoSQL or file storage means rewriting `Post`
- Every entity class duplicates the same SQL boilerplate

---

## After: Repository Pattern

### 1. Pure domain model

```python
@dataclass
class Post:
    id: str
    title: str
    content: str
    published_on: date
```

No storage details. Just data (and, where relevant, behavior).

### 2. Repository interface (port)

```python
from typing import Protocol

class PostRepository(Protocol):
    def get(self, post_id: str) -> Post: ...
    def add(self, post: Post) -> None: ...
    def update(self, post: Post) -> None: ...
    def delete(self, post_id: str) -> None: ...
    def find_published_since(self, since: date) -> list[Post]: ...
```

Include only the methods the use cases call, named in domain language. `find_published_since` pushes the query into storage. A `get_all()` followed by filtering in Python would leak query logic into services.

### 3. Concrete implementation (infrastructure)

Shown with raw `sqlite3` for clarity. With SQLModel, the same class would map between a `PostTable` and the `Post` domain object (see `layered-architecture.md` §5). Either way, the SQL lives **here** and never in services.

```python
import sqlite3

class SQLitePostRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_table()

    def _create_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS posts "
                "(id TEXT PRIMARY KEY, title TEXT, content TEXT, published_on TEXT)"
            )

    def get(self, post_id: str) -> Post:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if row is None:
            raise KeyError(f"Post not found: {post_id}")
        return Post(id=row[0], title=row[1], content=row[2], published_on=date.fromisoformat(row[3]))

    def add(self, post: Post) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO posts VALUES (?, ?, ?, ?)",
                         (post.id, post.title, post.content, post.published_on.isoformat()))

    def update(self, post: Post) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE posts SET title = ?, content = ?, published_on = ? WHERE id = ?",
                         (post.title, post.content, post.published_on.isoformat(), post.id))

    def delete(self, post_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))

    def find_published_since(self, since: date) -> list[Post]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, title, content, published_on FROM posts WHERE published_on >= ?",
                (since.isoformat(),),
            ).fetchall()
        return [
            Post(id=r[0], title=r[1], content=r[2], published_on=date.fromisoformat(r[3]))
            for r in rows
        ]
```

---

## Testing with a Fake Repository

```python
class InMemoryPostRepository:
    def __init__(self) -> None:
        self.posts: dict[str, Post] = {}

    def get(self, post_id: str) -> Post:
        if post_id not in self.posts:
            raise KeyError(f"Post not found: {post_id}")
        return self.posts[post_id]

    def add(self, post: Post) -> None:
        self.posts[post.id] = post

    def update(self, post: Post) -> None:
        if post.id not in self.posts:
            raise KeyError(f"Post not found: {post.id}")
        self.posts[post.id] = post

    def delete(self, post_id: str) -> None:
        if post_id not in self.posts:
            raise KeyError(f"Post not found: {post_id}")
        del self.posts[post_id]

    def find_published_since(self, since: date) -> list[Post]:
        return [p for p in self.posts.values() if p.published_on >= since]
```

Pass `InMemoryPostRepository` to services in unit tests, with no database needed. Test `SQLitePostRepository` separately with integration tests against a real database (`../testing-strategy.md`).

---

## Domain-Specific, Not Generic CRUD

A tempting shortcut is one generic contract for every entity:

```python
# AVOID as the default
DataObject = dict[str, Any]

class DataInterface(Protocol):
    def read_by_id(self, id: str) -> DataObject: ...
    def read_all(self) -> list[DataObject]: ...
    def create(self, data: DataObject) -> DataObject: ...
    def update(self, id: str, data: DataObject) -> DataObject: ...
    def delete(self, id: str) -> None: ...
```

It looks reusable, but:

- `dict[str, Any]` throws away type checking, so key typos and wrong shapes surface at runtime.
- Services can't express real queries, so they fetch everything and filter in Python.
- The port describes storage mechanics instead of what the use case needs.
- One implementation serves all entities, so entity-specific mapping and queries end up as special cases.

Prefer one small, typed port per aggregate (`PostRepository`, `BookingRepository`) with methods named after the questions the use cases ask.

---

## Generic Repository (Python 3.12+)

If several aggregates genuinely share the same basic needs, a **typed** generic base can remove duplication. Extend it with domain-specific methods, and don't let it replace them:

```python
class Repository[T](Protocol):
    def get(self, id: str) -> T: ...
    def get_all(self) -> list[T]: ...
    def add(self, item: T) -> None: ...
    def update(self, item: T) -> None: ...
    def delete(self, id: str) -> None: ...


class PostRepository(Repository[Post], Protocol):
    def find_published_since(self, since: date) -> list[Post]: ...
```

---

## When to Use

- **Use it** when you need to swap storage backends, test without a database, or decouple business logic from persistence
- **Skip it** for small scripts and tools without meaningful business logic, where a direct query in a well-named function is simpler. In an application, keep ORM sessions and queries out of services even if you never switch backends, because testability and separation are the main payoff.
- **Be aware** that a repository limits you to the methods you define. Add a new, well-named method when a use case needs a new query. Complex reporting or read-only queries may warrant a separate read model (`cqrs.md`).

## Relationship to Other Patterns

- **Unit of Work** (`unit-of-work.md`) — wraps multiple repository operations in a transaction
- **Adapter** (`adapter.md`) — a repository implementation is effectively an adapter between your domain and the storage system
- **Layered architecture** (`../layered-architecture.md`) — where ports and implementations live, mapping between SQLModel tables and domain objects
