---
name: decouple
description: Find tight coupling and suggest dependency injection improvements
argument-hint: [path]
---

Analyze the code at `$ARGUMENTS` (or the current working directory if no path given) for tight coupling and suggest how to decouple using dependency injection.

## Process

1. **Read the code** — Find and read ALL Python files in the target path recursively. Read every `.py` file. Map imports between modules.

2. **Identify coupling issues** — Look for:
   - **Concrete imports** — modules importing concrete classes instead of depending on abstractions
   - **Global mutable state** — module-level variables shared across files
   - **Content coupling** — accessing private members (`_var`) of other modules
   - **Law of Demeter violations** — chained attribute access (`a.b.c.method()`)
   - **Circular imports** — two modules importing each other
   - **God modules** — one module imported by nearly everything
   - **Missing composition root** — object creation scattered across multiple files instead of one place
   - **Hard-coded dependencies** — `import` inside functions, direct instantiation instead of injection

3. **Generate dependency map** — Show which modules depend on which:
   ```
   Module Dependencies
   ───────────────────
   api/routers/bookings.py → services/booking_service.py, api/schemas.py
   services/booking_service.py → repositories/bookings.py, domain/booking.py  (port only ✓)
   api/routers/admin.py → infrastructure/tables.py                            ⚠ adapter bypasses service
   services/report_service.py → infrastructure/sqlmodel_repositories.py      ⚠ concrete repository import
   ```

   Judge dependencies by direction, not folder names: inner code (domain, services) must never import outer code (infrastructure, frameworks, API). Concrete implementations should be created only in the composition root.

4. **Propose decoupling** — For each issue, show:
   - **File and line**
   - **Principle violated** — which of the 7 design principles (P1–P7)
   - **Current coupling** — what the code does now
   - **Decoupled version** — using a domain-specific Protocol (defined on the inner side), a Callable alias, or the composition root. Only introduce an abstraction where it buys something (a test fake, a second implementation, a layer boundary). Do not add one for every class.
   - **Before/after code**

5. **Ask before applying** — Use AskUserQuestion to confirm which changes to apply.

6. **Apply changes** — Edit the files with the approved decoupling.

For guidance on Protocol-based DI, consult `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/layered-architecture.md`, `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/dependency-injection.md` and `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/design-principles.md`.
