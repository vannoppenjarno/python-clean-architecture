# Advanced Testing

Beyond the per-layer testing strategy in `testing-strategy.md` (domain unit tests, service tests with in-memory fakes, repository integration tests, API tests), this file covers pytest organization, property-based testing with Hypothesis, model-based (stateful) testing, and code coverage philosophy.

---

## Pytest Organization

### Project Structure

Organize tests by test type, mirroring the architecture layers:

```
src/<package>/
  domain/
    booking.py
  services/
    booking_service.py
  repositories/
    bookings.py                      # port Protocol (no tests of its own)
  infrastructure/
    sqlmodel_repositories.py
  api/
    routers/bookings.py
tests/
  fakes.py                           # in-memory implementations of the ports
  conftest.py
  unit/
    test_booking.py                  # domain
    test_booking_service.py          # services, with fakes
  integration/
    conftest.py                      # real engine / session fixture
    test_sqlmodel_repositories.py    # repository implementations
  api/
    conftest.py                      # TestClient + app factory
    test_bookings_api.py
```

### Naming Conventions

- **Test files:** `test_<module_name>.py` (pytest discovers `test_` prefix by default)
- **Test functions:** `test_<what_it_tests>()` — descriptive names enable keyword filtering
- **One assert per test** — keeps tests focused and failure messages clear

### Useful CLI Options

| Command | Purpose |
|---------|---------|
| `pytest tests/` | Run all tests in folder |
| `pytest tests/test_foo.py::test_bar` | Run a single test |
| `pytest -k "customer and not delete"` | Filter by keyword |
| `pytest -v` | Verbose output with full test names |
| `pytest -s` | Show print/logging output |
| `pytest --durations=10` | Show 10 slowest tests |
| `pytest -x` | Stop on first failure |

### `conftest.py` and Fixtures

Shared test setup goes in `conftest.py`. Pytest auto-discovers it — no imports needed:

```python
# tests/conftest.py
import pytest

from tests.fakes import InMemoryBookingRepository, InMemoryRoomRepository

@pytest.fixture
def room() -> Room:
    return Room(id="r1", number="101", capacity=2, nightly_rate=Decimal("120.00"))

@pytest.fixture
def bookings() -> InMemoryBookingRepository:
    return InMemoryBookingRepository()

@pytest.fixture
def booking_service(room: Room, bookings: InMemoryBookingRepository) -> BookingService:
    return BookingService(InMemoryRoomRepository([room]), bookings, new_id=lambda: "b1")
```

**Usage in tests:**

```python
def test_book_room_persists_booking(booking_service, bookings):
    booking = booking_service.book_room(
        BookRoom("r1", "Jane Doe", StayPeriod(date(2025, 3, 1), date(2025, 3, 3)))
    )
    assert bookings.get("b1") == booking
```

### `@pytest.mark.parametrize`

Run the same test with multiple inputs:

```python
@pytest.mark.parametrize("price, quantity, expected", [
    (100, 2, 200),
    (50, 0, 0),
    (0, 5, 0),
    (99, 1, 99),
])
def test_compute_total(price, quantity, expected):
    assert compute_total(price, quantity) == expected
```

Parametrize eliminates copy-paste tests. Use for boundary conditions, equivalence classes, and edge cases.

---

## Property-Based Testing with Hypothesis

Instead of testing specific examples, test **properties** that should hold for any valid input. Hypothesis generates hundreds of random inputs automatically.

### Installation

```bash
uv add --dev hypothesis
```

### Basic Usage

```python
from hypothesis import given, settings, example
from hypothesis.strategies import text, integers

@given(text())
def test_encode_decode_roundtrip(s):
    """Property: decoding an encoded string returns the original."""
    assert decode(encode(s)) == s

@given(integers(min_value=0))
@example(0)  # always test this edge case
@settings(max_examples=200)
def test_price_is_non_negative(price):
    """Property: computed price is never negative."""
    assert compute_discounted_price(price) >= 0
```

### Common Strategies

| Strategy | Generates | Example |
|----------|-----------|---------|
| `text()` | Unicode strings | `"hello"`, `""`, `"\x00"` |
| `integers()` | Arbitrary ints | `0`, `-42`, `2**64` |
| `integers(min_value=1, max_value=100)` | Bounded ints | `1`, `50`, `100` |
| `floats(min_value=0, allow_nan=False)` | Safe floats | `0.0`, `3.14` |
| `sampled_from(["a", "b", "c"])` | Pick from list | `"b"` |
| `lists(integers(), min_size=1)` | Non-empty int lists | `[3, -1, 7]` |

### Custom Composite Strategies

Build complex test data generators:

```python
from hypothesis import composite

@composite
def orders(draw, min_items=1, max_items=5):
    """Generate Order objects with random line items."""
    items = [
        LineItem(
            description=draw(text(min_size=1, max_size=50)),
            price=draw(integers(min_value=1, max_value=10000)),
            quantity=draw(integers(min_value=1, max_value=20)),
        )
        for _ in range(draw(integers(min_value=min_items, max_value=max_items)))
    ]
    return Order(customer="Test", line_items=items)

@given(orders())
def test_order_total_is_sum_of_items(order):
    expected = sum(item.price * item.quantity for item in order.line_items)
    assert order.total == expected
```

### Properties Worth Testing

- **Roundtrip / inverse:** `decode(encode(x)) == x`
- **Invariants:** list length preserved after sort, total equals sum of parts
- **Idempotency:** `f(f(x)) == f(x)` for operations like normalization
- **Commutativity:** `merge(a, b) == merge(b, a)` when order shouldn't matter
- **Bounds:** output is always within expected range

---

## Model-Based (Stateful) Testing

Tests many inputs **with many different action sequences**. Uses a state machine to generate valid sequences of operations and check invariants throughout.

### Testing Pyramid

```
Unit Tests:            one input, one fixed action sequence
Property-Based Tests:  many inputs, one fixed action sequence
Model-Based Tests:     many inputs, many action sequences
```

### Hypothesis Stateful Testing

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition
from hypothesis.strategies import integers, text, sampled_from, data

class OrderStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.order = Order(customer="Test")
        self.items: list[LineItem] = []

    @rule(
        description=text(min_size=1),
        price=integers(min_value=1, max_value=10000),
        quantity=integers(min_value=1, max_value=20),
    )
    def create_item(self, description, price, quantity):
        item = LineItem(description, price, quantity)
        self.items.append(item)

    @precondition(lambda self: len(self.items) > 0)
    @rule(data=data())
    def add_item_to_order(self, data):
        item = data.draw(sampled_from(self.items))
        self.order.add_line_item(item)

    @precondition(lambda self: len(self.order.line_items) > 0)
    @rule(data=data())
    def remove_item_from_order(self, data):
        item = data.draw(sampled_from(self.order.line_items))
        self.order.remove_line_item(item)

    @invariant()
    def total_is_correct(self):
        expected = sum(i.price * i.quantity for i in self.order.line_items)
        assert self.order.total == expected

    @precondition(lambda self: len(self.order.line_items) == 0)
    @invariant()
    def empty_order_has_zero_total(self):
        assert self.order.total == 0

# Pytest discovery
TestOrder = OrderStateMachine.TestCase
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `RuleBasedStateMachine` | Base class — Hypothesis generates sequences of `@rule` calls |
| `@rule` | An action Hypothesis can apply (with generated arguments) |
| `@invariant` | Checked after every rule — must always hold |
| `@precondition` | Rule only applies when condition is true |
| `data()` strategy | Allows drawing from dynamic state (e.g., `sampled_from(self.items)`) |

**Why it's powerful:** Hypothesis found bugs where the same item added twice to an order caused incorrect totals — a sequence humans rarely think to test.

---

## Code Coverage Philosophy

### What Coverage Measures

Coverage tracks which lines of code were **executed** during tests — not whether they were **correctly validated**.

```bash
uv add --dev pytest-cov
uv run pytest --cov=src --cov-report=html tests/
```

### Why 100% Coverage Misleads

A function can have 100% line coverage and still contain critical bugs:

```python
def compute_tax(price: int, exemption: int, rate: float) -> float:
    return (price - exemption) * rate  # 100% covered!
    # BUG: returns negative tax when exemption > price
    # FIX: return max(0, (price - exemption) * rate)
```

Tests that execute this line achieve coverage — but only a test with `exemption > price` catches the bug.

### What to Focus On

1. **Branch coverage** over line coverage — test both sides of every `if/else`
2. **Edge cases and boundaries** — zero, negative, empty, maximum values
3. **Error paths** — test that exceptions are raised for invalid input
4. **Meaningful assertions** — `assert result == expected`, not just `assert result`

### Practical Guidelines

- Use coverage reports to **find untested code paths**, not as a quality metric
- **Unit tests must be deterministic** — never use `random.randint()` or `random.choice()` as test input; use fixed values so failures reproduce identically in CI
- **Property-based tests (Hypothesis) are a controlled exception** — Hypothesis uses seeds, shrinking, and a failure database to ensure reproducibility despite generating varied inputs. This is fundamentally different from naive randomness.
- Combine coverage with property-based testing to catch bugs that example-based tests miss

---

## Test-Driven Development (Red-Green-Refactor)

TDD follows five steps in a cycle:

1. **Write tests** that only pass if the feature specification is met — forces you to think about requirements before coding
2. **Run the tests and verify they all fail** — confirms you are testing new functionality
3. **Write the simplest code** that makes the tests pass — does not have to be perfect yet
4. **Verify all tests pass** — including older tests, ensuring new code does not break existing behavior
5. **Refactor** while keeping tests green — improve structure with a safety net

### TDD Anti-Patterns

**Do not reuse mutable state between tests:**

```python
# BAD: shared instance leaks mutations between tests
employee_to_test = Employee(name="Test", pay_rate=50.0)

def test_payout_no_hours():
    assert employee_to_test.compute_payout() == 1000  # uses leaked state

# GOOD: each test creates its own instance
def test_payout_no_hours():
    emp = Employee(name="Test", pay_rate=50.0)
    assert emp.compute_payout() == 1000
```

**Do not test Python built-in behavior:**

```python
# BAD: testing that dataclass assignment works
def test_employee_attributes():
    emp = Employee(name="Jane", pay_rate=50.0)
    assert emp.name == "Jane"  # tests Python, not your code

# GOOD: test your business logic
def test_compute_payout_with_commission():
    emp = Employee(name="Jane", pay_rate=50.0, hours_worked=10,
                   has_commission=True, contracts_landed=5, commission=100)
    assert emp.compute_payout() == 1500  # tests computed value
```

**Always compare against fixed values, never re-implement the logic in the test:**

```python
# BAD: duplicating the implementation in the test
def test_payout():
    assert emp.compute_payout() == compute_payout_reference(emp)
    # Comparing two copies of the same code

# GOOD: assert against a pre-computed constant
def test_payout():
    emp = Employee(pay_rate=50.0, hours_worked=10, employer_cost=1000)
    assert emp.compute_payout() == 1500
```

### When TDD Costs More Than It Saves

- At startups in early-stage product discovery, requirements change so fast that maintaining exhaustive tests becomes overhead
- TDD creates a false sense of security if you only write unit tests and skip integration/end-to-end testing
- When the test author is also the code author, blind spots are likely

---

## Mutation Testing

Mutation testing modifies your source code slightly (introducing "mutants") and checks whether your tests catch the change. It is a test for your tests.

A mutation testing tool makes small changes to operators and values (`+` → `-`, `<` → `<=`, `x * 2` → `x + 2`). If your tests still pass after a mutation, you have a **surviving mutant** — your tests are not thorough enough.

```python
def multiply_by_two(x: int) -> int:
    return x * 2

# This test does NOT catch `x + 2` replacing `x * 2`:
def test_multiply():
    assert multiply_by_two(2) == 4  # 2+2 == 4 also passes!

# Adding a second case kills the mutant:
def test_multiply_three():
    assert multiply_by_two(3) == 6  # 3+2 != 6, mutant caught
```

```bash
uv add --dev mutmut
uv run mutmut run --paths-to-mutate=src/
```

---

## API Testing with FastAPI

### In-Memory SQLite via the App Factory

Build a fresh app per test with an in-memory SQLite URL. The app factory's lifespan creates the engine and tables, so no global state is shared between tests:

```python
# tests/api/conftest.py
from fastapi.testclient import TestClient

from hotel.api.app import create_app
from hotel.infrastructure.settings import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(Settings(database_url="sqlite://"))
    with TestClient(app) as client:   # runs lifespan → creates engine + tables
        yield client
```

```python
def test_book_room_returns_201(client: TestClient) -> None:
    room = client.post("/rooms", json={"number": "101", "capacity": 2, "nightly_rate": "100.00"}).json()
    body = {"room_id": room["id"], "guest_name": "Ada", "check_in": "2025-03-01", "check_out": "2025-03-03"}

    response = client.post("/bookings", json=body)

    assert response.status_code == 201
    assert response.json()["total_price"] == "200.00"


def test_unknown_booking_returns_404(client: TestClient) -> None:
    assert client.get("/bookings/does-not-exist").status_code == 404
```

### Overriding Dependencies

To test an endpoint without a database, override the service provider from `api/dependencies.py` with one built on in-memory fakes:

```python
app.dependency_overrides[get_booking_service] = lambda: BookingService(
    InMemoryRoomRepository([room]), InMemoryBookingRepository(), new_id=lambda: "b1"
)
```

### Test Services Directly (Not Through Routes)

Because services are separated from routes and depend only on ports, test the business behavior without HTTP and without a database:

```python
def test_book_room_rejects_overlap(booking_service: BookingService) -> None:
    booking_service.book_room(BookRoom("r1", "Ada", StayPeriod(date(2025, 3, 1), date(2025, 3, 3))))

    with pytest.raises(RoomUnavailable):
        booking_service.book_room(BookRoom("r1", "Bob", StayPeriod(date(2025, 3, 2), date(2025, 3, 5))))
```

This is faster and more focused than going through the HTTP client. Keep API tests for status codes, schemas and error mapping, and test SQL in repository integration tests.

---

## Relationship to Other Testing Approaches

- **`testing-strategy.md`** covers what to test at each layer, with in-memory fakes for service tests — the foundation for testing use cases without a database
- **Property-based testing** complements fakes: use fakes for isolation, Hypothesis for input variety (domain value objects such as `StayPeriod` are ideal targets)
- **Model-based testing** is most valuable for stateful systems (orders, workflows, state machines from `patterns/state.md`)
