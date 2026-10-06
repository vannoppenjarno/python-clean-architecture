---
name: add-endpoint
description: Scaffold a new use case and endpoint across the architecture layers
argument-hint: <use-case or entity>
---

Add a new use case for `$ARGUMENTS` and expose it as an endpoint, working inside out through the architecture layers: domain → port → service → infrastructure → API → tests → wiring.

## Process

1. **Understand the project.** Read the existing structure before writing anything:
   - Find the package root (`src/<package>/` or a flat package) and locate the domain, services, repository ports, infrastructure and API modules. Folder names vary (`use_cases/` instead of `services/`, `adapters/` instead of `infrastructure/`). Follow what the project uses.
   - Note conventions: naming, how ports are defined, how "not found" is signalled (returns `None` or raises), command dataclasses vs. explicit parameters, service classes vs. functions, error mapping, how the composition root (`api/dependencies.py` or equivalent) builds services, and where fakes and tests live.
   - **Simplified structure:** if the project uses merged modules (`domain.py`, `services.py`, `infrastructure.py`, `api.py`) or is a small CLI, add the code to those modules in the same order rather than creating new folders. Do not grow the structure unless a module has become too large or mixes concerns. If so, propose the split and let the user decide.
   - **Different architecture:** if the project does not separate these concerns at all, say so, briefly describe the target from `layered-architecture.md`, and ask whether to follow the existing style or introduce the layers for this use case only.

2. **Ask for details.** Use AskUserQuestion to clarify:
   - What the use case does, in business terms (e.g. "cancel a booking", "list available rooms for a period"), and which HTTP method and path it should use.
   - Which business rules and failure cases apply (not found, conflict, invalid input).
   - Whether it needs new persistence (new table or query) or only existing ports.

   Prefer meaningful use cases over a generic CRUD set. Generate full CRUD only if the user explicitly asks for it.

3. **Generate across the layers, inside out:**

   **Domain** (`domain/`)
   - Add or extend dataclass entities and value objects, and put the rules next to the data.
   - Add domain exceptions for the new failure cases. These are plain Python with no framework imports.

   **Port** (`repositories/` or `services/ports.py`)
   - Add only the methods this use case needs, named in domain language and typed with domain objects (no `dict[str, Any]`, no ORM types).

   **Service** (`services/`)
   - Implement the use case against the ports, with a typed input (command dataclass or parameters).
   - Raise domain exceptions. No SQL, sessions, `HTTPException` or status codes.
   - A pass-through read with no rules may stay very thin. Do not invent ceremony.

   **Infrastructure** (`infrastructure/`, only if persistence changes)
   - Extend or add the SQLModel table, and implement the new port methods in the repository implementation.
   - Push filtering into SQL and map rows to and from domain objects explicitly.

   **API** (`api/`)
   - Add Pydantic v2 request and response schemas, with `from_domain()` on the response.
   - Add a thin router endpoint (schema → command → service → schema) with correct method and status codes (201 create, 204 delete, 200 read/update).
   - Map new domain exceptions to HTTP statuses in the central error handlers.
   - Add or extend the service provider in the composition root.

   **Tests**
   - `tests/unit/`: domain rules, and the service with the in-memory fakes. Extend `tests/fakes.py` so the fakes implement the new port methods.
   - `tests/integration/`: the new repository methods against a real or in-memory engine.
   - `tests/api/`: happy path, validation (422) and each mapped domain error.

4. **Wire it.** Include the new router in the app factory (or `main`) if it is new, and register providers in the composition root. Concrete classes are created only there.

5. **Confirm before writing.** Use AskUserQuestion to show the list of files to create or modify, then apply the changes.

Follow existing project conventions for naming, imports and style. Consult:
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/layered-architecture.md`, section 9: "Adding a New Use Case: Checklist"
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/testing-strategy.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/examples/fastapi-hotel-api/` for a working reference
