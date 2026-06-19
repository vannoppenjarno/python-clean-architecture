---
name: learn-architecture
description: Learn an architecture or design topic — theory, the Pythonic way, and how it applies in your code
argument-hint: [topic]
---

Teach the user an architecture or design topic from this skill's knowledge base. This command **explains and deepens understanding** — it does not refactor, review, or scaffold. The goal is for the user to understand both the *theory* and how it works *in practice*, including the trade-offs and comparisons an interviewer (or a thoughtful teammate) would probe.

The user may have given a topic in `$ARGUMENTS` (e.g. `strategy`, `dependency injection`, `the 7 principles`, `drill me on repository`). It may also contain a mode hint like `drill` or `lesson`.

## Hard rule — this command never edits

This is a **read-only, teaching command**. It reads the user's code and the bundled example to explain — it must **never** create, modify, or delete any file as part of teaching. Showing "before/after" snippets, pointing at a violation, or saying "here's how you'd fix it" is explanation, not editing — present it in your reply, never apply it.

The only exception: the user **explicitly** asks you to apply a change to their code during the session (e.g. "go ahead and refactor that file", "apply that fix"). Even then:

- **Stop and confirm first.** Use AskUserQuestion to show exactly which file(s) and what change, and get an explicit yes before any edit. A vague "sure" or momentum from the lesson is not consent — confirm the specific change.
- **This confirmation is mandatory even in auto-accept / auto-edit mode.** Do not rely on the permission prompt to gate the edit — proactively ask via AskUserQuestion yourself, because that prompt may be suppressed. No silent edits, ever.
- **Prefer to redirect.** Applying refactors is the job of the action commands. Point the user to `/make-pythonic`, `/extract-god-class`, `/decouple`, `/add-endpoint`, or `/scaffold-api` instead — only edit from this command if they decline the redirect and still want it here.

## Step 1 — Pick the mode

Unless the arguments already make it obvious, use AskUserQuestion to ask **"How do you want to learn this?"** with two options:

1. **Lesson** — "A structured walkthrough: theory → Pythonic code → how it shows up in your project → trade-offs → a few questions to self-check."
2. **Drill me** — "Interactive. I explain a little, then ask you to answer or explain, react to what you say, and go deeper until it's solid. Good for active rehearsal."

## Step 2 — Pick the topic

If `$ARGUMENTS` names a topic, match it to the catalog below (fuzzy match — `pubsub` → Notification, `DI` → Dependency Injection, `3-layer` → Layered Architecture).

If no topic is given, use AskUserQuestion to ask **"What do you want to learn?"** with these buckets:

1. **Principles & Architecture** — the 7 design principles, GRASP, three-layer architecture, dependency injection, DDD, domain modeling, project organization
2. **Pythonic Patterns** — the 25 patterns (Strategy, Factory, Repository, State, Adapter, etc.)
3. **Code Quality & Refactoring** — the 22 rules, code smells, refactoring case studies, error handling
4. **APIs, Testing & Python craft** — REST design, testable APIs, Pydantic, classes/dataclasses, functions, types, context managers, decorators, async, pattern matching

After the bucket is chosen, name the specific topic. If the bucket is **Pythonic Patterns**, list the 25 patterns grouped (see catalog) and let the user pick one — don't force a four-option picker on 25 patterns.

### Topic → reference file catalog

All paths are under `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/references/`. Read the authoritative file(s) for the chosen topic before teaching — do not rely on memory alone.

**Principles & Architecture**
- The 7 design principles → `design-principles.md`
- GRASP principles → `grasp-principles.md`
- Three-layer architecture (Routers → Operations → Database) → `layered-architecture.md`
- Dependency injection → `dependency-injection.md`
- Domain-Driven Design → `domain-driven-design.md`
- Domain modeling (entities, value objects, relationships) → `domain-modeling.md`
- Project organization (modules, packages, the "utils" trap) → `project-organization.md`

**Pythonic Patterns** (each → `patterns/<name>.md`; `pythonic-patterns.md` is the quick-reference lookup)
- Behavioral: `strategy`, `state`, `command`, `template-method`, `notification` (Pub/Sub), `pipeline`, `functional` (Callback / Wrapper / Builder)
- Creational: `abstract-factory`, `builder`, `registry`, `singleton`, `plugin-architecture`
- Structural: `adapter`, `bridge`, `facade`, `repository`, `fluent-interface`
- Architectural / domain: `value-objects`, `event-sourcing`, `cqrs`, `unit-of-work`, `retry`, `lazy-loading`

**Code Quality & Refactoring**
- 22 code quality rules → `code-quality.md`
- Code smells catalog → `code-smells.md`
- Refactoring case studies → `refactoring-case-studies.md`
- Error handling (exceptions, context managers) → `error-handling.md`
- Railway-oriented / monadic error handling → `monadic-error-handling.md`

**APIs, Testing & Python craft**
- REST API design → `rest-api-design.md`
- Testable API / stub-based testing → `testable-api.md`
- Advanced testing (pytest, property-based, stateful) → `testing-advanced.md`
- Pydantic validation → `pydantic-validation.md`
- Classes vs dataclasses → `classes-and-dataclasses.md`
- Function design (pure functions, closures, partial, HOFs) → `function-design.md`
- Data structures → `data-structures.md`
- Types & type hints → `types-and-type-hints.md`
- Context managers → `context-managers.md`
- Decorators → `decorators.md`
- Async patterns → `async-patterns.md`
- Pattern matching (`match`/`case`) → `pattern-matching.md`

## Step 3 — Ground it in two places

Always anchor the topic in concrete code, using **two** anchors so it's both canonical and personal:

1. **Always: the bundled example.** Use `${CLAUDE_PLUGIN_ROOT}/skills/clean-architecture/examples/fastapi-hotel-api/` (and the topic's reference file) for a clean, correct illustration of the concept. This is the canonical "here's what good looks like" — show it every time, even when the user's project also has an example.

2. **Also: the user's project.** Scan the Python files in the working directory and report which of these is true (cite `file:line`):
   - **Already applied** — it's in use here; point to it and assess whether it's done well.
   - **Could apply** — there's a spot where it would be a reasonable fit (note the trade-off — sometimes the simpler version is fine; flag if applying it would be over-engineering).
   - **Should apply** — there's a real violation or pain point this concept would fix (e.g. a long `if/elif` crying out for Strategy/Registry, a router importing the DB directly).
   - **Doesn't apply here** — say so honestly, and use the bundled example alone rather than forcing a weak match.

   If there's no project open at all, say so and teach from the bundled example only.

Keep the two anchors distinct: the example shows the textbook form; the project analysis answers "what does this mean for *my* code right now?"

## Step 4 — Teach

### Lesson mode

Walk through the topic in this structure. Keep each part tight — this is a lesson, not a reference dump. Favor one good code example over five.

1. **In one sentence** — the concept distilled.
2. **The problem it solves** — the *why*. What pain or change-pressure motivates it? (This is the part interviewers care about most.)
3. **How it works** — the mechanics and key vocabulary.
4. **The Pythonic way** — the idiomatic implementation, illustrated with the bundled example (anchor 1 from Step 3). Prefer Protocol/Callable/`functools.partial`/dict-dispatch over ABC-heavy OOP, per this skill's defaults. Show the real example code.
5. **In your project** — anchor 2 from Step 3. State which case holds — *already applied*, *could apply*, *should apply* (a violation to fix), or *doesn't apply here* — and show the actual code at `file:line`. This is where the textbook concept becomes "what it means for my codebase right now."
6. **Trade-offs & "commonly confused with"** — costs, when *not* to use it (YAGNI / KISS), and the comparison that trips people up: Strategy vs State, Adapter vs Facade, Repository vs the `DataInterface` Protocol, Factory vs Builder, Value Object vs Entity, composition vs inheritance, etc. Pick the comparison(s) that fit the topic.
7. **Check your understanding** — 3–4 questions an interviewer might ask, plus one **"explain it back in your own words"** prompt. Offer: *"Want me to drill you on these interactively? Re-run with Drill mode."*

### Drill mode

Be a Socratic tutor, not a lecturer. Protocol:

- Open with **one or two sentences** of framing, then immediately ask the first question. Do not pre-explain the whole topic.
- **Ask one question at a time, then stop and wait for the answer.** Never answer your own question or stack multiple questions in one turn.
- Sequence the questions to build depth: start with *"what problem does this solve?"*, then mechanics, then *"what's the Pythonic way to do it here?"*, then trade-offs and *"when would you use X over Y?"*.
- **React to each answer** before moving on: affirm what's correct, gently correct what's off, and fill the gap with a crisp explanation (and a code snippet when it helps).
- Use both anchors: point to the bundled example for the clean form, and push them to find the spot in *their* code — *"Find the `if/elif` in your code that this pattern would replace — which one is it?"* (or, if it doesn't apply to their project, *"where might you reach for this in future work?"*).
- After roughly 4–6 exchanges, close with a short **scorecard**: what they nailed, what to review, and which reference file to read for the gap.

In both modes, write naturally and concretely — cite real files and lines, show real code, and keep the interview-prep value implicit (theory + practice + trade-offs + comparisons) without framing it as test cramming.
