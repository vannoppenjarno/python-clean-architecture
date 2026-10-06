---
name: review-architecture
description: Review code against Python Clean Architecture principles
argument-hint: [path]
---

Before starting the review, use AskUserQuestion to ask: "Which review depth?" with these options:
1. **Standard** — "Reviews against built-in checklists. No extra permissions needed."
2. **In-depth** — "Loads detailed reference files for deeper analysis with refactoring recipes and pattern guidance."

Then review the code at `$ARGUMENTS` (or the current working directory if no path given) against Python Clean Architecture principles.

## Review Process

1. **Read the code** — Find and read ALL Python files in the target path recursively. Read every `.py` file — do not skip any. Understand the project structure, imports, and relationships between files.

2. **Check the dependency rule.** Dependencies must point inward only: Infrastructure / frameworks / DB → Adapters (API, CLI, repository implementations) → Services / use cases → Domain. Verify:
   - **Domain is framework-free.** It does not import FastAPI, Pydantic, SQLModel/SQLAlchemy, HTTP clients or I/O. It uses plain dataclasses, enums and domain exceptions, and holds its own invariants and rules.
   - **Services depend on ports.** They receive domain-specific `Protocol`s or `Callable`s through constructor or parameters. No SQL, ORM sessions, `select()`, `HTTPException` or status codes. No importing from `infrastructure/` or `api/`. No instantiating concrete repositories or clients.
   - **Ports are domain-specific and typed.** Methods are named after use-case questions (`find_overlapping`, `get_by_email`) and accept and return domain objects. Flag generic `dict[str, Any]` CRUD contracts (`read_all()` then filtering in Python) and ports that leak ORM types.
   - **SQLModel/ORM only in infrastructure.** Tables are persistence models, mapped explicitly to and from domain objects in the repository implementation. Flag a single model used as ORM table, API schema and domain entity at once.
   - **Pydantic at the boundaries.** Request and response schemas, settings and external payloads use Pydantic and are mapped to domain objects in the adapter. No Pydantic models in the domain or as service inputs.
   - **Adapters stay thin.** Routers translate HTTP to use-case calls with no business rules and no persistence logic. Domain exceptions are mapped to HTTP once (exception handlers), not scattered.
   - **Single composition root.** Concrete implementations are created and wired in one place (`api/dependencies.py`, `main()`, a `bootstrap` module), not scattered across routers and services.
   - **Structure is proportional to project size.** Flag missing structure (business rules in routers, services importing SQLModel, tests needing a DB to check a calculation). Also flag **over-engineering**: empty or one-trivial-file layers, Protocols with one implementation and no fake, pass-through services that only forward, or mapping code longer than the logic in a small script or CLI.
   - **Patterns are justified.** Each abstraction or pattern solves a nameable problem (second implementation, test seam, growing `if/elif`, transaction boundary). Flag speculative ones.

3. **Check the 7 design principles** — For each file/class/function, evaluate:
   - **High Cohesion** — Does each unit have a single responsibility?
   - **Low Coupling** — Are dependencies minimized? Any Law of Demeter violations?
   - **Depend on Abstractions** — Protocol/Callable used for DI? Or concrete imports?
   - **Composition over Inheritance** — Any deep hierarchies or mixins?
   - **Separate Creation from Use** — One composition root? Dict mapping over if/elif?
   - **Start with the Data** — Prefixed fields? Parallel lists? Methods far from data?
   - **Keep Things Simple** — Over-engineered? Speculative features? Unnecessary abstractions?

4. **Check code quality** — Apply the 22 design rules:
   - No type abuse, vague identifiers, flag parameters, deep nesting
   - Tell don't ask, no parallel data structures, no god classes
   - No broad exception catching, no mutable defaults, no wildcard imports
   - Type hints on all functions, enums for fixed options, context managers for resources

5. **Check Pythonic patterns** — Are patterns implemented the Pythonic way?
   - Strategy as Callable, not ABC hierarchy
   - Factory as dict mapping, not if/elif
   - Protocol over ABC (unless shared state needed)
   - functools.partial for configuration, closures for builders
   - Pub/Sub for notification side effects, not inline calls
   - Registry for data-driven object creation, not if/elif
   - Context managers for resource management, not try/finally
   - Custom exception classes, not broad except catching
   - Dataclasses for value objects and DTOs, not manual __init__
   - Pure functions where possible, side effects pushed to boundaries

6. **Check code cleanup opportunities** — Look for concrete refactoring targets:
   - Extract class when a class does two things
   - Extract function when a function does two things
   - Replace mutable globals with injected dataclass context
   - Replace boolean flag parameters with separate functions
   - Replace string constants with Enums
   - Replace deep nesting (3+ levels) with early returns or extraction
   - Replace god classes (too many responsibilities) with collaborators
   - Move methods to the class that owns the data (Information Expert)
   - Replace parallel data structures with a single data class
   - Replace if/elif chains with dict mapping

7. **Report findings** — Structure the output in this order:

   ### Architecture Summary
   Classify every Python file into a layer, then show the dependency flows. Use a simple vertical list format — never multi-column ASCII art. Example:

   ```
   Layers
   ──────
   Domain:          domain/booking.py, domain/room.py, domain/errors.py
   Services:        services/booking_service.py
   Ports:           repositories/bookings.py, repositories/rooms.py
   Infrastructure:  infrastructure/tables.py, infrastructure/sqlmodel_repositories.py, infrastructure/settings.py
   API (adapter):   api/app.py, api/dependencies.py, api/schemas.py, api/routers/bookings.py, api/routers/rooms.py
   Unclear:         utils/helpers.py (mixed concerns)

   Dependency Flows
   ────────────────
   api/routers/rooms.py → services/room_service.py → repositories/rooms.py → domain/room.py   ✓
   infrastructure/sqlmodel_repositories.py → domain/, infrastructure/tables.py                 ✓
   api/dependencies.py → services/, infrastructure/  (composition root)                        ✓
   api/routers/bookings.py → infrastructure/tables.py                                          ⚠ adapter bypasses service
   services/booking_service.py → sqlmodel                                                      ⚠ infrastructure leak
   domain/booking.py → pydantic                                                                ⚠ framework in domain

   Layer Violations
   ────────────────
   ⚠ api/routers/bookings.py queries BookingTable directly — should call BookingService via a port
   ⚠ services/booking_service.py builds select() statements — move the query into a repository method behind BookingRepository
   ```

   Adapt to the actual project and its folder names. If it does not follow this layout (a simplified structure, a CLI, or another architecture), show the dependency flow as-is, judge it against the dependency rule rather than the folder names, and note what a proportionate target structure would look like. Keep it compact: group similar flows rather than listing every file when there are many.

   ### What Works Well
   Call out specific things the code does right. Reference files and patterns. Examples:
   - Framework-free domain with invariants enforced in dataclasses
   - Services depending on domain-specific repository Protocols, tested with in-memory fakes
   - Explicit mapping between SQLModel tables and domain objects in the repository implementation
   - Pydantic schemas kept at the API boundary (Create vs Out models with `from_domain()`)
   - One composition root wiring concrete implementations
   - Structure kept small where the project is small
   - Meaningful naming, good type hint coverage

   This section builds trust and avoids a purely negative tone. Be specific — cite actual files and lines, not generic praise.

   ### Findings by Severity
   Present issues organized by severity:
   - **Critical** — Dependency rule violations (framework/ORM in domain, SQL/ORM or `HTTPException` in services, adapters bypassing services), business rules in routers, services coupled to concrete DB
   - **Important** — Generic `dict[str, Any]` ports, missing boundary mapping, scattered wiring (no single composition root), over-engineered structure for the project size, cohesion issues, Law of Demeter violations, missing type hints
   - **Suggestions** — Pattern improvements, naming, simplification opportunities, cleanup refactorings

   For each finding, include all of the following:
   1. **File and line** — exact location
   2. **Principle(s)** — which of the 7 design principles are violated, by number and name (e.g., "P1 High Cohesion", "P3 Depend on Abstractions"). Can be more than one.
   3. **Pattern** — if a Pythonic design pattern would help, name it (e.g., "Strategy pattern — use Callable type alias", "Registry pattern — dict mapping replaces if/elif"). Not every finding needs a pattern.
   4. **Fix** — show the recommended fix with a code snippet

   Prioritize actionable cleanup suggestions over architectural observations.

## In-Depth Mode

If the user chose in-depth, load the following reference files for deeper analysis with detailed refactoring recipes and pattern guidance:
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/layered-architecture.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/design-principles.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/code-quality.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/error-handling.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/pythonic-patterns.md`

For detailed pattern guidance (when explaining HOW to fix), consult the relevant files in `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/patterns/`.

If the user chose standard, use only the checklists above — do not load reference files.
