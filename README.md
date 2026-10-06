# python-clean-architecture — Claude Code Plugin

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that provides a Clean Architecture engineering standard for Python repositories, with or without FastAPI. Scaffold, review and refactor Python projects with an inward-pointing layered architecture, design principles and Pythonic patterns, directly inside Claude Code.

## Attribution

The design principles and Pythonic patterns in this plugin are inspired by [Arjan Codes](https://www.arjancodes.com/)' courses:

- **The Software Designer Mindset**: seven core design principles (cohesion, coupling, abstractions, composition, creation/use separation, data-first design, simplicity)
- **Pythonic Patterns**: classic GoF patterns reimagined for Python using Protocol, Callable, functools.partial and closures

The architecture has been adapted into a generic engineering standard: Clean Architecture layers with domain-specific ports, a uv/`src`-layout project setup and a per-layer testing strategy. This plugin distills those ideas into actionable guidance for Claude Code. It is not a reproduction of course content. If you find this useful, consider supporting Arjan's work at [arjancodes.com](https://www.arjancodes.com/), [github.com/arjancodes](https://github.com/arjancodes), and [youtube.com/arjancodes](https://www.youtube.com/arjancodes).

## Installation

1. Add the marketplace:
```
/plugin marketplace add MKToronto/python-clean-architecture
```

2. Install the plugin:
```
/plugin install python-clean-architecture@python-clean-architecture
```

3. Restart Claude Code (`/exit` then `claude`) to load the plugin.

Or download the repo and test locally without installing:

```bash
git clone https://github.com/MKToronto/python-clean-architecture.git
claude --plugin-dir /path/to/python-clean-architecture
```

## Updating

```
/plugin marketplace update python-clean-architecture
```

Then restart Claude Code (`/exit` then `claude`).

## Usage

### Automatic (Skill)

The skill triggers automatically when you ask Claude Code to:

- "Scaffold a Python project" / "Scaffold a FastAPI project"
- "Set up clean architecture"
- "Refactor to clean architecture"
- "Add a new use case / endpoint / service / repository"
- "Review my code structure"
- "Apply design patterns in Python"
- "Decouple my code"
- "Make my code testable"

Or mention: layered architecture, ports and adapters, dependency inversion, dependency injection, Protocol-based design, uv/pyproject setup, Pythonic design patterns.

### Slash Commands

```
/review-architecture              Review current directory
/review-architecture src/         Review a specific directory
/review-architecture app/main.py  Review a specific file
```

The review checks:
- **Dependency rule** — Framework-free domain; services depend on domain-specific ports (no SQL/ORM or `HTTPException`); SQLModel only in infrastructure; Pydantic only at boundaries; one composition root; structure proportional to project size (over-engineering is flagged too); every pattern justified
- **7 design principles** — Cohesion, coupling, abstractions, composition, creation/use, data-first, simplicity
- **22 code quality rules** — Naming, nesting, types, error handling, imports, structure
- **Pythonic patterns** — All 25 patterns checked (Strategy as Callable, Factory as dict mapping, Protocol over ABC, etc.)

Findings are reported by severity (Critical / Important / Suggestions) with file/line references and fix snippets.

### All Commands

**Review & Analysis:**
```
/review-architecture [path]       Full architecture review (standard or in-depth)
/review-api-design [path]         Review REST API endpoints for HTTP conventions
/check-quality [path]             Quick check against 22 code quality rules
/suggest-patterns [path]          Recommend Pythonic design patterns for your code
/decouple [path]                  Find tight coupling and suggest DI improvements
```

**Refactoring:**
```
/make-pythonic [path]             Refactor to Pythonic patterns (ABC→Protocol, if/elif→dict, etc.)
/extract-god-class [path]         Find and split god classes into focused collaborators
```

**Learning:**
```
/learn-architecture [topic]       Learn a design or architecture topic — theory + the Pythonic way + your code
```

`/learn-architecture` explains rather than edits. Pick any topic from the skill (the 7 principles, Clean Architecture layers, project setup, testing strategy, the 25 Pythonic patterns, GRASP, DDD, code smells, REST, Python craft) and get either a **Lesson** (structured walkthrough) or a **Drill** (interactive Socratic Q&A). Every topic is grounded twice: a canonical illustration from the bundled example service, plus an analysis of *your* code — whether the concept already applies, could apply, or should apply (a violation to fix). Each lesson ends with trade-offs, the "commonly confused with" comparison (Strategy vs State, Adapter vs Facade…), and self-check questions.

**Scaffolding & Testing:**
```
/scaffold-api <project-name>      Generate a FastAPI service (uv, pyproject.toml, src layout, clean layers)
/add-endpoint <use-case>          Scaffold a new use case and endpoint across the architecture layers
/scaffold-tests [path]            Generate tests per layer (domain, services with fakes, repositories, API)
```

`/scaffold-api` asks for your entities, use cases and whether you need persistence, then recommends `uv init --package` and `uv add` commands (it never installs without your consent) and generates only what is needed: domain dataclasses and errors, domain-specific repository ports, services, SQLModel tables with repository implementations and explicit mapping, a FastAPI adapter (schemas, routers, error handlers, composition root, app factory), and unit, integration and API tests.

`/add-endpoint` adds a use case to an existing project, inside out: domain → port → service → infrastructure → API → tests → wiring. It follows the project's conventions and adapts to a simplified structure.

`/scaffold-tests` detects your test conventions and generates domain unit tests, service tests with in-memory fakes implementing your ports, repository integration tests and API tests. It asks before writing.

## What's Inside

```text
python-clean-architecture/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── README.md
├── LICENSE
├── commands/
│   ├── review-architecture.md
│   ├── review-api-design.md
│   ├── check-quality.md
│   ├── suggest-patterns.md
│   ├── decouple.md
│   ├── make-pythonic.md
│   ├── extract-god-class.md
│   ├── diagnose-smells.md
│   ├── refactor-legacy.md
│   ├── learn-architecture.md
│   ├── scaffold-api.md
│   ├── scaffold-tests.md
│   └── add-endpoint.md
└── skills/clean-architecture/
    ├── SKILL.md
    ├── references/
    │   ├── layered-architecture.md
    │   ├── project-setup.md
    │   ├── testing-strategy.md
    │   ├── testing-advanced.md
    │   ├── design-principles.md
    │   ├── dependency-injection.md
    │   ├── domain-modeling.md
    │   ├── rest-api-design.md
    │   ├── code-quality.md
    │   ├── code-smells.md
    │   ├── refactoring-case-studies.md
    │   ├── classes-and-dataclasses.md
    │   ├── function-design.md
    │   ├── data-structures.md
    │   ├── error-handling.md
    │   ├── monadic-error-handling.md
    │   ├── types-and-type-hints.md
    │   ├── project-organization.md
    │   ├── context-managers.md
    │   ├── decorators.md
    │   ├── async-patterns.md
    │   ├── pydantic-validation.md
    │   ├── pattern-matching.md
    │   ├── grasp-principles.md
    │   ├── domain-driven-design.md
    │   ├── pythonic-patterns.md
    │   └── patterns/          (25 pattern files)
    │       ├── strategy.md
    │       ├── registry.md
    │       ├── command.md
    │       ├── builder.md
    │       ├── repository.md
    │       ├── cqrs.md
    │       └── ...
    └── examples/
        └── fastapi-hotel-api/
            ├── pyproject.toml
            ├── src/hotel/
            │   ├── domain/            # dataclasses, value objects, rules, domain errors
            │   ├── services/          # use cases, depend on ports only
            │   ├── repositories/      # domain-specific port Protocols
            │   ├── infrastructure/    # SQLModel tables, repository impls, settings
            │   └── api/               # FastAPI app factory, routers, schemas, dependencies
            └── tests/
                ├── fakes.py           # in-memory implementations of the ports
                ├── unit/
                ├── integration/
                └── api/
```

## Key Concepts

### Clean Architecture Layers

Source-code dependencies point **inward only**:

```
Infrastructure / frameworks / database      (SQLModel, HTTP clients, files, settings)
    ↓
Adapters / interfaces                       (FastAPI routers, CLI, repository implementations)
    ↓
Services / use cases                        (application logic, orchestration)
    ↓
Domain                                      (entities, value objects, business rules)
```

- **Domain** is pure Python (dataclasses, enums, domain exceptions), with no FastAPI, Pydantic or SQLModel.
- **Services** implement use cases against **ports**: domain-specific `Protocol`s such as `BookingRepository.find_overlapping(...)`, not generic `dict[str, Any]` CRUD. No SQL, sessions or `HTTPException`.
- **Infrastructure** holds SQLModel tables and repository implementations, which map explicitly to and from domain objects.
- **API** (FastAPI) is an outer adapter. Pydantic schemas live at the boundary, and `api/dependencies.py` is the single composition root.

Typical request flow:

```
HTTP request
  → FastAPI router (adapter: validate input with Pydantic, map to a command)
  → service / use case
  → domain (rules, calculations, invariants)
  → repository port (Protocol, defined inside)
  → concrete repository (SQLModel implementation, outside)
```

Recommended layout for a normal application: `src/<package>/{domain,services,repositories,infrastructure,api}` with `tests/{unit,integration,api}`. Scripts, CLIs and small services use a deliberately simpler structure (see `project-setup.md`).

### Default Python Stack

| Concern | Default | Add only when |
|---|---|---|
| Environment and dependencies | **uv** + `pyproject.toml` (no `requirements.txt`) | always |
| Layout | `src/` layout | always |
| Testing | **pytest** | always |
| HTTP API | **FastAPI** | the project exposes HTTP |
| Validation / serialization | **Pydantic v2** at the boundaries | data crosses a boundary that needs validation |
| Relational persistence | **SQLModel** in infrastructure | the project stores relational data |

### Testing Strategy

- **Domain**: plain unit tests
- **Services**: unit tests with in-memory fakes of the ports (`tests/fakes.py`)
- **Repositories**: integration tests against a real or in-memory database
- **API**: tests via `TestClient`

### Pragmatism

Scale the structure to the problem. A script stays one module, and a small CLI gets a few cohesive modules. Only a real service gets the full layout. Introduce a pattern or abstraction only when you can name the concrete problem it solves (KISS/YAGNI). Reviews flag over-engineering as well as missing structure.

### Seven Design Principles

1. High Cohesion — Single responsibility per unit
2. Low Coupling — Minimize dependencies, Law of Demeter
3. Depend on Abstractions — Protocol + Callable for DI
4. Composition over Inheritance — Never mixins, shallow hierarchies only
5. Separate Creation from Use — Dict mapping, creator functions, one composition root
6. Start with the Data — Information Expert, fix data structures first
7. Keep Things Simple — DRY, KISS, YAGNI (but avoid hasty abstractions)

### Pythonic Pattern Defaults

- Protocol over ABC (unless shared superclass state needed)
- `functools.partial` over wrapper classes
- Closures over factory class hierarchies
- `Callable` type aliases over single-method abstract classes
- Dict mapping over if/elif chains
- Readability over dogmatic functional purity

25 design patterns implemented the Pythonic way:

**Core Patterns:**
- **Strategy** — `Callable` type alias, pass functions as args
- **Abstract Factory** — Tuples of functions + `functools.partial`
- **Bridge** — `Callable` type alias replaces abstract reference
- **Command** — Functions returning undo closures
- **Pub/Sub** — Dict-based `subscribe(event, handler)` / `post_event(event, data)`
- **Registry** — `dict[str, Callable]` mapping + `**kwargs` unpacking
- **Template Method** — Free function + Protocol parameter
- **Pipeline** — `functools.reduce` for composition
- **Callback / Wrapper / Builder** — Functional patterns for event handling, interface translation, and configuration

**Extended Patterns:**
- **Value Objects** — Subclass built-in types with `__new__` validation, or frozen dataclass
- **Event Sourcing** — Immutable events, append-only EventStore, projection functions
- **CQRS** — Separate write model + read projection, projector function after writes
- **Builder** — Fluent API with `Self` return type, `.build()` returns frozen product
- **Unit of Work** — Context manager wrapping transaction: commit on success, rollback on error
- **Singleton** — Module-level instance (preferred), or metaclass with `_instances` dict
- **State** — Protocol-based state objects, context delegates to current state
- **Adapter** — Protocol interface + `functools.partial` for single-method adaptation
- **Facade** — Simplified interface class, `functools.partial` to bind dependencies
- **Retry** — `@retry` decorator with exponential backoff, fallback strategies
- **Lazy Loading** — `functools.cache`, `cached_property`, generators, `__getattr__`
- **Repository** — Domain-specific Protocol port, implementations in infrastructure per storage backend
- **Fluent Interface** — Methods return `self` for chaining, domain-specific verbs for readability
- **Plugin Architecture** — Config-driven creation, `importlib` auto-discovery, self-registering modules

## Example Output

See the [full example review](https://mktoronto.github.io/python-clean-architecture/#example) — a color-coded `/review-architecture` run against a test bookstore-api project (15 findings with before/after code).

## Also available for

- **Codex CLI** — [python-clean-architecture-codex](https://github.com/MKToronto/python-clean-architecture-codex) (agent skill for Codex)
