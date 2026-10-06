---
name: Python Clean Architecture
description: This skill should be used when the user asks to "scaffold a Python project", "scaffold a FastAPI project", "set up clean architecture", "refactor to clean architecture", "add a use case", "add a service", "add an endpoint", "add a repository", "review my code structure", "apply design patterns in Python", "decouple my code", "improve code quality", "make my code testable", or mentions layered architecture, ports and adapters, dependency inversion, dependency injection, Protocol-based design, uv/pyproject project setup, or Pythonic design patterns for Python projects (with or without FastAPI, Pydantic or SQLModel).
version: 1.0.0
---

# Python Clean Architecture

A reusable engineering standard for Python repositories. It covers how to structure code so business logic sits at the center, frameworks stay at the edges, and every part is testable. It applies to any Python project. Do not assume one project's structure for every repository.

> **Attribution:** Many of the design principles and Pythonic pattern implementations come from [Arjan Codes](https://www.arjancodes.com/)' courses (*The Software Designer Mindset*, *Pythonic Patterns*). This standard adapts them and is not a reproduction of course content.

## The Dependency Rule

Source code dependencies point **inward only**:

```
Infrastructure / frameworks / database      (SQLModel, HTTP clients, files, queues)
    ↓
Adapters / interfaces                       (FastAPI routers, CLI, repository implementations)
    ↓
Services / use cases                        (application logic, orchestration)
    ↓
Domain                                      (entities, value objects, business rules)
```

- **Domain** is the core. It imports nothing from frameworks, databases, HTTP, FastAPI, SQLModel or Pydantic. It uses only plain Python: dataclasses, enums, the standard library, and its own exceptions.
- **Services** implement use cases. They orchestrate domain objects and talk to the outside world only through **ports**, which are `Protocol`s defined on the inner side. They never contain SQL, ORM queries, sessions or HTTP concepts.
- **Adapters** translate between the outside world and the services: a FastAPI router, a CLI command, or a repository implementation.
- **Infrastructure** holds the concrete technology: database engine and session, SQLModel tables, external API clients, settings.
- An outer layer may import an inner layer. An inner layer never imports an outer one.

Typical request flow:

```
HTTP request
  → FastAPI router (adapter: validate input, map to domain/command)
  → service / use case
  → domain (rules, calculations, invariants)
  → repository port (Protocol, defined inside)
  → concrete repository (SQLModel/SQL/HTTP implementation, outside)
```

## Layer Rules

| Layer | Owns | Must NOT |
|---|---|---|
| Domain | Entities, value objects, domain exceptions, pure business rules | Import frameworks, ORM, Pydantic, I/O; know about persistence or HTTP |
| Services | Use cases, orchestration, non-repository ports (`services/ports.py`: clock, ID factory, external gateways) | Contain SQL/ORM code, raise `HTTPException`, instantiate concrete infrastructure |
| Repositories (ports) | Domain-specific `Protocol` interfaces such as `BookingRepository` | Expose ORM types or generic `dict[str, Any]` payloads |
| Infrastructure | SQLModel tables, sessions, repository implementations, external clients, settings | Contain business rules |
| API / adapters | Routers, request/response schemas (Pydantic), error → status mapping, composition root | Contain business rules or persistence logic |

The rules that matter most:

1. **Define ports where they are used.** Repository and external-service interfaces live on the inner side. Implementations live outside.
2. **Prefer domain-specific ports over generic CRUD.** Write `bookings.find_overlapping(room_id, period)`, not `repo.read_all()` followed by filtering. Add only the methods your use cases call.
3. **Prefer strong types over `dict[str, Any]`.** Pass domain objects, value objects, dataclasses or typed commands between layers. Untyped dicts are acceptable only at the outermost boundary, for example raw JSON before validation.
4. **Map at the boundary.** Pydantic schemas map to and from domain objects in the API layer. SQLModel tables map to and from domain objects in the repository implementation. Neither leaks inward.
5. **One composition root.** Concrete implementations are created and wired in one place: FastAPI dependency providers, `main()`, or a `bootstrap` module. Services receive their dependencies through the constructor or as parameters.

Full detail with code: `references/layered-architecture.md`.

## Pragmatism: Scale the Structure to the Problem

Layers are a tool, not a religion. Choose the smallest structure that keeps the dependency rule intact:

| Project shape | Recommended structure |
|---|---|
| Script / one-off tool (< ~300 lines, no persistence) | Single module. Keep pure logic in functions separate from I/O in `main()`. |
| Small CLI or library | `src/<package>/` with a few cohesive modules (e.g. `models.py`, `logic.py`, `io.py`). Introduce a `Protocol` only where tests need a fake. |
| Normal application or service | The full recommended layout below. |
| Large or multi-domain system | Split by bounded context first (`src/<package>/<context>/`), with the layer folders inside each context. |

Recommended layout for a normal application:

```
src/<package>/
    domain/            # entities, value objects, domain exceptions, pure rules
    services/          # use cases; depend on ports only
    repositories/      # port Protocols (domain-specific interfaces)
    infrastructure/    # db engine/session, SQLModel tables, repo implementations, clients, settings
    api/               # FastAPI app, routers, Pydantic schemas, dependency wiring
tests/
    unit/              # domain + services (fakes for ports)
    integration/       # repository implementations against a real/ephemeral DB
    api/               # HTTP-level tests via TestClient
```

Leave out folders the project doesn't need. A project without HTTP has no `api/`. A project without persistence has no `infrastructure/db`. Add a layer when it removes real pain, not ahead of time.

## Default Python Stack

| Concern | Default | Add only when |
|---|---|---|
| Environment and dependencies | **uv** + `pyproject.toml` (no `requirements.txt`) | always |
| Layout | `src/` layout, single importable package | always |
| Testing | **pytest** | always |
| HTTP API | **FastAPI** (outer adapter) | the project exposes HTTP |
| Validation/serialization | **Pydantic v2** (boundaries: API schemas, settings, external payloads) | data crosses a boundary that needs validation |
| Relational persistence | **SQLModel** (infrastructure only) | the project stores relational data |

Do not add FastAPI, SQLModel or Pydantic to a repository that has no need for that concern. Setup details, `pyproject.toml` template and tooling: `references/project-setup.md`.

## Testing Rules

- **Domain**: plain unit tests. No framework, no database, no fixtures beyond simple objects.
- **Services**: unit tests with **in-memory fakes** that implement the port Protocols. Prefer fakes over `unittest.mock`.
- **Repository implementations**: **integration tests** against a real engine, such as SQLite in-memory or a containerized database.
- **API adapters**: API tests via `fastapi.testclient.TestClient`, overriding the service or repository dependencies where useful.
- Inject time, IDs and randomness so tests stay deterministic.

Details and examples: `references/testing-strategy.md`, `references/testing-advanced.md`.

## Design Principles

Apply these when writing or reviewing code, roughly in priority order:

1. **High cohesion.** Each module, class or function has one responsibility.
2. **Low coupling.** Minimize what each unit knows about others. Pass only what is needed.
3. **Depend on abstractions (dependency inversion).** Use `Protocol` for architectural boundaries and `Callable` aliases for single-behavior dependencies. The consumer owns the abstraction.
4. **Composition over inheritance.** Build behavior from collaborating objects. Use no mixins and keep hierarchies shallow. Use an ABC only when shared implementation genuinely belongs in a base class.
5. **Separate creation from use.** Wire concrete objects in the composition root and nowhere else.
6. **Start with the data.** Model the domain types first, and behavior follows the data (Information Expert).
7. **Keep it simple: KISS, YAGNI, sensible DRY.** Build only what is needed now. Avoid hasty abstractions.

Full treatment: `references/design-principles.md`, `references/grasp-principles.md`.

## Patterns: Only When They Solve a Real Problem

Do not introduce a design pattern because it exists. Before adding an abstraction or pattern, name the concrete problem it solves, such as a second implementation, a test seam, a growing `if/elif` chain, or a transaction boundary. If you can't name one, write the straightforward code.

| Symptom you actually have | Consider | Pythonic form |
|---|---|---|
| Growing `if/elif` selecting behavior | Strategy | `Callable` alias, dict of functions |
| Creating objects from config/JSON | Registry | `dict[str, Callable]` + `**kwargs` |
| Persistence logic mixed into domain/services | Repository | Domain-specific `Protocol` + implementation in infrastructure |
| Several writes must succeed/fail together | Unit of Work | Context manager owning the session/transaction |
| Third-party API doesn't fit your port | Adapter | Class implementing your Protocol, wrapping the client |
| Bare primitives for domain concepts | Value Object | Frozen dataclass with validation |
| Side effects tangled with core logic | Notification / events | Domain events + handlers wired at the root |
| Transient external failures | Retry | Decorator with backoff at the adapter boundary |
| Object behavior depends on its state | State | Protocol-based state objects |

Defaults: `Protocol` over ABC, `functools.partial` and closures over wrapper classes, and readability over functional purity. The complete table and full pattern write-ups are in `references/pythonic-patterns.md` and `references/patterns/`.

## Review Checklist (Quick)

- [ ] Domain imports no framework, ORM, Pydantic or I/O module
- [ ] Services depend on Protocols, not concrete repositories or clients
- [ ] No SQL, ORM session or query code outside `infrastructure/`
- [ ] No `HTTPException` or HTTP status codes outside `api/`
- [ ] Ports are domain-specific and typed, with no `dict[str, Any]` CRUD contracts
- [ ] Concrete wiring lives in one composition root
- [ ] Structure is proportional to project size, with no empty ceremonial layers
- [ ] Every abstraction or pattern has a stated reason
- [ ] Domain and services are unit-tested without a database. Repositories have integration tests.

## Reference Files

**Architecture and structure**
- `references/layered-architecture.md`: layers, ports, mapping, composition root, request flow, full code
- `references/project-setup.md`: uv, `pyproject.toml`, `src/` layout, tooling, scaling down
- `references/project-organization.md`: modules, packages, imports, layer-first vs context-first
- `references/dependency-injection.md`: DI vs DIP, Protocols, composition root, FastAPI `Depends`
- `references/domain-modeling.md`, `references/domain-driven-design.md`: modeling the core
- `references/design-principles.md`, `references/grasp-principles.md`: principles with refactoring recipes
- `references/rest-api-design.md`: HTTP conventions for the API adapter

**Testing**
- `references/testing-strategy.md`: what to test at each layer, fakes, integration and API tests
- `references/testing-advanced.md`: pytest organization, Hypothesis, stateful testing, coverage

**Python craft**
- `references/types-and-type-hints.md`, `references/classes-and-dataclasses.md`, `references/function-design.md`, `references/data-structures.md`
- `references/error-handling.md`, `references/monadic-error-handling.md`, `references/context-managers.md`, `references/decorators.md`
- `references/async-patterns.md`, `references/pydantic-validation.md`, `references/pattern-matching.md`
- `references/code-quality.md`, `references/code-smells.md`, `references/refactoring-case-studies.md`

**Patterns**
- `references/pythonic-patterns.md`: lookup table of all patterns
- `references/patterns/*.md`: one file per pattern (repository, unit-of-work, adapter, strategy, registry, value-objects, …)

## Example

- `examples/fastapi-hotel-api/`: a small uv/`src`-layout service showing a domain with rules, services that depend on ports, SQLModel repositories in infrastructure, a FastAPI adapter with a composition root, and unit, integration and API tests.
