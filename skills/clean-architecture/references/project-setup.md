# Project Setup Reference

The default way to set up a Python repository under this standard: **uv**, **`pyproject.toml`**, a **`src/` layout** and **pytest**. Add frameworks only for concerns the project actually has.

---

## 1. Create the Project with uv

```bash
uv init --package my-service        # application with an importable package under src/
uv init --lib my-library            # reusable library (also src/ layout)
cd my-service
uv python pin 3.12                  # writes .python-version
```

Add dependencies **by concern**. Only add what the project needs:

```bash
# HTTP API needed?
uv add "fastapi[standard]"          # includes uvicorn and the `fastapi dev` CLI
# Validation/serialization at a boundary but no FastAPI? (FastAPI already brings Pydantic)
uv add pydantic
# Relational persistence needed?
uv add sqlmodel

# Dev tooling (dependency group, not shipped)
uv add --dev pytest pytest-cov ruff mypy
```

Everyday commands:

| Task | Command |
|---|---|
| Create/refresh `.venv` from the lockfile | `uv sync` |
| Run anything in the project env | `uv run <cmd>`, e.g. `uv run pytest` |
| Add / remove a dependency | `uv add <pkg>` / `uv remove <pkg>` |
| Upgrade locked versions | `uv lock --upgrade` (or `--upgrade-package <pkg>`) |
| CI install (fail if lock is stale) | `uv sync --locked` |
| Run the API in dev | `uv run fastapi dev src/<package>/api/app.py` or `uv run uvicorn <package>.api.app:app --reload` |

Rules:

- **No `requirements.txt`.** `pyproject.toml` declares dependencies and `uv.lock` pins them. Commit both.
- If a platform needs a requirements file, generate it with `uv export --format requirements-txt`. Never edit it by hand.
- Don't `pip install` into the project environment. Use `uv add` / `uv sync`.
- `.venv/` is not committed.

---

## 2. `pyproject.toml` Template

```toml
[project]
name = "my-service"
version = "0.1.0"
description = "One sentence on what this service does."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    # only what the project needs, e.g.:
    # "fastapi>=0.115",
    # "sqlmodel>=0.0.22",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-cov>=5",
    "ruff>=0.6",
    "mypy>=1.11",
    # "httpx>=0.27",   # needed by fastapi.testclient when FastAPI is used
]

[build-system]
# Keep whatever `uv init --package` generated (uv_build); hatchling is equally fine:
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
markers = [
    "integration: tests that need real infrastructure (database, network)",
]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "RUF"]

[tool.mypy]
strict = true
packages = ["my_service"]
```

Notes:

- `requires-python = ">=3.12"` allows modern typing (`class Repo[T](Protocol)`, `type` aliases). Lower it only if a deployment target requires that.
- With the `src/` layout and a build backend, `uv sync` installs the package in editable mode, so tests import `my_service` exactly as production does. No `sys.path` hacks or `pythonpath` settings are needed.
- `mypy --strict` (or pyright) is strongly recommended. Protocol-based boundaries only pay off when a type checker verifies them.

---

## 3. Repository Layout

### Normal application

```
my-service/
├── pyproject.toml
├── uv.lock
├── .python-version
├── README.md
├── .gitignore
├── src/
│   └── my_service/
│       ├── __init__.py
│       ├── domain/            # entities, value objects, domain errors, rules
│       ├── services/          # use cases (+ services/ports.py for non-repository ports)
│       ├── repositories/      # repository port Protocols
│       ├── infrastructure/    # db, SQLModel tables, repository impls, clients, settings
│       └── api/               # FastAPI app factory, routers, schemas, dependencies
└── tests/
    ├── conftest.py
    ├── fakes.py               # in-memory implementations of ports
    ├── unit/                  # domain + services
    ├── integration/           # repository implementations, external clients
    └── api/                   # HTTP tests
```

### Scaled down

Use the smallest structure that keeps business logic separate from I/O.

**Script.** Use a single file, and `uv init --script` if you want inline dependency metadata:

```
tool.py        # pure functions + main() doing I/O
```

**Small CLI or library:**

```
src/my_tool/
    __init__.py
    models.py      # dataclasses
    logic.py       # pure functions
    cli.py         # argparse/typer adapter = composition root
tests/
    test_logic.py
```

**Small service with one or two aggregates.** Merge folders while keeping the dependency direction:

```
src/my_service/
    domain.py
    services.py        # use cases + port Protocols
    infrastructure.py  # SQLModel tables + repository implementations
    api.py             # FastAPI app, schemas, wiring
```

Grow into the full layout when a file passes a few hundred lines or mixes concerns.

### Large system: split by bounded context first

```
src/my_platform/
    billing/
        domain/ services/ repositories/ infrastructure/ api/
    inventory/
        domain/ services/ repositories/ infrastructure/ api/
    shared/            # only genuinely shared kernel types (Money, ids); keep it tiny
    main.py            # composes the contexts' routers into one app
```

---

## 4. Which Stack Pieces to Add

| The project... | Add |
|---|---|
| exposes HTTP endpoints | FastAPI (+ uvicorn), and `httpx` in dev for `TestClient` |
| validates or serializes external data (requests, files, third-party payloads, settings) | Pydantic v2 (already present with FastAPI) |
| stores relational data | SQLModel, plus Alembic once the schema evolves in production |
| needs many env-driven settings | `pydantic-settings`, or a frozen dataclass with `from_env()` if the settings are few |
| has none of the above | Nothing. A plain-Python package with pytest is a complete project. |

Never add a framework "for later" (YAGNI).

---

## 5. Optional: Enforce the Dependency Rule

When the team is larger or the codebase is growing, make layer violations fail CI with [`import-linter`](https://import-linter.readthedocs.io/):

```toml
[tool.importlinter]
root_package = "my_service"

[[tool.importlinter.contracts]]
name = "Clean Architecture layers"
type = "layers"
layers = [
    "my_service.api",
    "my_service.infrastructure",
    "my_service.services",
    "my_service.repositories",
    "my_service.domain",
]

[[tool.importlinter.contracts]]
name = "Domain is framework-free"
type = "forbidden"
source_modules = ["my_service.domain"]
forbidden_modules = ["fastapi", "sqlmodel", "sqlalchemy", "pydantic"]
```

```bash
uv add --dev import-linter
uv run lint-imports
```

`api` is listed above `infrastructure` because the API's composition root wires infrastructure into services. Infrastructure must never import `api`.

---

## 6. `.gitignore` Essentials

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
.env
*.db
```

---

## 7. CI Skeleton

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=src/my_service --cov-report=term-missing
```
