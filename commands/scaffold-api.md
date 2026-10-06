---
name: scaffold-api
description: Generate a new FastAPI service with clean architecture (uv, pyproject.toml, src layout)
argument-hint: <project-name>
---

Generate a new FastAPI service named `$ARGUMENTS`. Use a uv-managed `pyproject.toml`, a `src/` layout and Clean Architecture layers. Dependencies point inward: infrastructure → adapters (API, repository implementations) → services → domain.

Only generate what the project needs. Every layer, dependency and pattern must solve a concrete problem the user has described (KISS/YAGNI).

## Process

1. **Ask for the domain.** Use AskUserQuestion to find out:
   - "What are the main entities or concepts?" (e.g. rooms, bookings, customers)
   - "What use cases should the service support?" (e.g. book a room, cancel a booking, list available rooms). Prefer use cases in business language over generic CRUD.
   - "Are there business rules or invariants?" (e.g. no overlapping bookings, price = nightly rate x nights)

2. **Ask about persistence and size.** Use AskUserQuestion:
   - "Does the service need to store data?" with options: **Relational DB (SQLModel)**, **No persistence / in-memory only**, **Other (external API, files)**. Only add SQLModel when persistence is needed.
   - If the answers describe a very small service (one or two aggregates, few rules), propose the simplified layout from `project-setup.md` (`domain.py`, `services.py`, `infrastructure.py`, `api.py`) and let the user choose between simplified and full.

3. **Set up the project with uv (recommend, do not run without consent).** Show the commands and ask the user before running any of them. Never run installs silently:

   ```bash
   uv init --package {project-name}
   cd {project-name}
   uv add fastapi uvicorn            # HTTP API
   uv add sqlmodel                   # only if relational persistence is needed
   uv add --dev pytest pytest-cov httpx ruff mypy
   ```

   Do **not** create `requirements.txt`, and do not use `pip install`. If the user declines running the commands, write the `pyproject.toml` (template in `project-setup.md`) with the dependencies listed and tell them to run `uv sync`.

4. **Create the structure.** Full layout for a normal service:

   ```
   {project-name}/
   ├── pyproject.toml
   ├── .python-version
   ├── .gitignore
   ├── README.md
   ├── src/
   │   └── {package}/
   │       ├── __init__.py
   │       ├── domain/
   │       │   ├── __init__.py
   │       │   ├── errors.py              # DomainError base + specific domain exceptions
   │       │   └── {entity}.py            # dataclasses, value objects, business rules
   │       ├── repositories/
   │       │   ├── __init__.py
   │       │   └── {entities}.py          # domain-specific port Protocols
   │       ├── services/
   │       │   ├── __init__.py
   │       │   └── {entity}_service.py    # use cases + input command dataclasses
   │       ├── infrastructure/            # only if persistence/external systems are needed
   │       │   ├── __init__.py
   │       │   ├── settings.py            # frozen dataclass with from_env()
   │       │   ├── db.py                  # engine creation, create_tables
   │       │   ├── tables.py              # SQLModel table=True persistence models
   │       │   └── sqlmodel_repositories.py  # port implementations + explicit mapping
   │       └── api/
   │           ├── __init__.py
   │           ├── app.py                 # create_app() factory, lifespan, routers, error handlers
   │           ├── dependencies.py        # composition root: session + service providers
   │           ├── errors.py              # domain exception -> HTTP status mapping
   │           ├── schemas.py             # Pydantic v2 request/response models + from_domain()
   │           └── routers/
   │               ├── __init__.py
   │               └── {entities}.py      # thin endpoints: schema -> command -> service -> schema
   └── tests/
       ├── conftest.py
       ├── fakes.py                       # in-memory implementations of the ports
       ├── unit/                          # domain + service tests (no DB)
       ├── integration/                   # repository tests against SQLite in-memory
       └── api/                           # TestClient tests via create_app()
   ```

   Leave out what is not needed. Without persistence there is no `infrastructure/db.py`, `tables.py` or `tests/integration/`. In that case the composition root wires an in-memory repository, or the service has no repository at all.

5. **Generate the files, inside out:**
   - **Domain.** Pure Python `@dataclass` entities (usually `frozen=True`), value objects and enums. Validate invariants in `__post_init__` or factory functions. Put behavior next to its data, for example `room.price_for(period)`. Add domain exceptions in `domain/errors.py`. Import no FastAPI, Pydantic, SQLModel or I/O modules.
   - **Ports.** One `Protocol` per aggregate, with only the methods the use cases call, named in domain language (`find_overlapping`, `get_by_email`). They accept and return domain objects, never `dict[str, Any]` or ORM rows. Use a `Callable` alias for single-behavior dependencies such as `IdFactory` or `Clock`.
   - **Services.** Use cases that take typed inputs (a command dataclass or explicit parameters) and receive their ports through the constructor. They raise domain exceptions. No SQL, sessions, `select()`, `HTTPException` or status codes. Keep them thin, and move pure rules into the domain.
   - **Infrastructure (if persistence).** SQLModel `table=True` classes in `tables.py`. Repository implementations in `sqlmodel_repositories.py` that satisfy the ports structurally, push queries into SQL and map rows to and from domain objects with explicit private functions (`_to_domain`, `_to_row`). Settings come from the environment. For in-memory SQLite, use `StaticPool` so sessions share one connection.
   - **API adapter.** Pydantic v2 request and response schemas, with `from_domain()` on response models. Thin routers that map request → command → service → response. `dependencies.py` is the **single composition root**: it builds the session and constructs services with concrete repositories and ID factories. Exception handlers map domain errors to HTTP statuses once (not found → 404, conflict → 409, validation → 422). `create_app(settings=None)` registers the lifespan (engine and tables), routers and handlers.
   - **Tests.**
     - `tests/unit/`: domain rules (no fixtures), and services with the fakes from `tests/fakes.py`. Inject deterministic IDs and time.
     - `tests/integration/`: each repository implementation against an in-memory SQLite session, covering round-trip mapping and every query method. Mark these tests `@pytest.mark.integration`.
     - `tests/api/`: `TestClient(create_app(Settings(database_url="sqlite://")))`, covering the happy path, 422 validation and domain-error status mapping per endpoint.
   - **pyproject.toml.** Add pytest config (`testpaths`, `integration` marker) and ruff/mypy settings as in `project-setup.md`.

6. **Confirm before writing.** Use AskUserQuestion to show the file list (and the uv commands, if not yet run) and get approval before creating files.

7. **Explain how to run it.** Mention `uv sync`, `uv run pytest`, `uv run fastapi dev src/{package}/api/app.py` (or `uv run uvicorn {package}.api.app:app --reload`), and, for production, Alembic migrations instead of `create_tables`.

## References

- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/layered-architecture.md`: layers, ports, mapping, composition root, request flow
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/project-setup.md`: uv, `pyproject.toml` template, layouts (full and simplified), `.gitignore`
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/testing-strategy.md`: tests per layer, fakes, integration and API tests
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/examples/fastapi-hotel-api/`: working reference with the same layout (`src/hotel/{domain,services,repositories,infrastructure,api}`, `tests/{fakes.py,unit,integration,api}`)

Use the example for structure and idioms. Do not copy its domain into the new project.
