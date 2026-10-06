---
name: scaffold-tests
description: Generate tests per architecture layer (domain, services with in-memory fakes, repositories, API)
argument-hint: [path]
---

Generate tests for the code at `$ARGUMENTS` (or the current working directory if no path given), organized by architecture layer. Business logic is tested fast and without a database. Infrastructure is tested against a real engine.

## Process

1. **Read the code.** Find and read all Python files in the target path recursively. Classify them:
   - **Domain**: entities, value objects, pure rules and domain exceptions
   - **Ports**: `Protocol`s or `Callable` aliases that services depend on (repositories, gateways, clocks, ID factories)
   - **Services / use cases**: code that orchestrates domain objects through ports
   - **Repository implementations / clients**: SQLModel/SQLAlchemy/SQL or HTTP code in infrastructure
   - **API adapters**: FastAPI routers, the app factory, dependency providers, error handlers

2. **Detect existing conventions.** Read `pyproject.toml` (pytest config, markers, test paths), `tests/conftest.py`, any `tests/fakes.py` and existing tests. Match their layout (`tests/unit|integration|api` or a flat `tests/`), naming, fixture style and import style (installed package imports such as `from <package>.domain...`, not `sys.path` hacks). Do not duplicate tests that already exist.

   If services create their dependencies internally (sessions, clients, `datetime.now()`, `uuid4()`), they cannot be unit-tested with fakes. Report this and suggest the minimal refactor (inject the dependency, introduce a domain-specific port; see `testing-strategy.md`, section 6). Ask before changing production code.

3. **Plan tests per layer:**

   **Domain unit tests** (`tests/unit/`)
   - Construct objects and assert behavior, with no fixtures or frameworks.
   - Cover invariants (invalid construction raises the domain exception), calculations with known inputs, boundaries (`@pytest.mark.parametrize`).

   **Service unit tests with fakes** (`tests/unit/` + `tests/fakes.py`)
   - For each port the services use, write an **in-memory fake** that implements the project's actual Protocol: same method names, signatures, domain types and "not found" convention. Use no inheritance and no generic dict-based stub.
   - Inject deterministic ID factories and clocks.
   - Cover the happy path (assert the returned domain object and the state stored in the fake), each domain error path, and edge cases (empty, duplicates, conflicts).
   - Prefer fakes over `unittest.mock`. Use mocks only to assert outbound side effects or to simulate failures.

   **Repository integration tests** (`tests/integration/`)
   - Use a session fixture on an in-memory SQLite engine (`StaticPool`) with tables created, or the project's real database via testcontainers if it relies on DB-specific behavior.
   - Cover round-trip mapping (`add` then `get` returns an equal domain object), every query method including boundaries, and not-found behavior.
   - Mark the tests `@pytest.mark.integration` and register the marker in `pyproject.toml` if it is missing.

   **API tests** (`tests/api/`)
   - Use `TestClient` built from the app factory with a test database URL, or override service providers via `app.dependency_overrides` with services built from fakes.
   - Per endpoint, cover the success status and response shape, 422 on invalid payloads, and each domain error mapped to its status (404, 409, ...). Do not re-test business rules exhaustively here.

   Skip layers the project does not have (no API → no API tests; no persistence → no integration tests).

4. **Ask before writing.** Use AskUserQuestion to confirm: "Generate these test files?" Show the list of files (including `tests/fakes.py` and any `conftest.py` changes) and the layer each one covers.

5. **Write the test files** and tell the user how to run them: `uv run pytest`, `uv run pytest tests/unit`, `uv run pytest -m "not integration"`. If `pytest` or `httpx` is missing from the dev dependency group, recommend `uv add --dev pytest httpx`. Do not run it without consent.

For testing patterns and advanced techniques, consult:
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/testing-strategy.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/testing-advanced.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/examples/fastapi-hotel-api/tests/` (working reference: `fakes.py`, `unit/`, `integration/`, `api/`)
