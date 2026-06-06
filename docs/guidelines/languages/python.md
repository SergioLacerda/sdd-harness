# Python Engineering Guidelines

**DSL guidelines active when wizard language = Python:** G01, G05, G09, G13, G17
**Universal principles:** see [core-engineering-principles.md](../core-engineering-principles.md) (M018)

---

## 1. Code Style (G05 — SOFT)

**Tools required:**

```bash
ruff check .
ruff format --check .
mypy .
```

**Rules:**

- All public functions and methods must have type annotations.

- No `bare except` — always catch specific exceptions.

- No `Any`as a default type. Use`Protocol` for structural contracts.

- No import-time side effects (network I/O, global mutation, env reads at import).

- Use typed models (`dataclass`, `TypedDict`, `pydantic.BaseModel`) for structured data.

- Inject dependencies via parameter — never via `import module_with_global_state`.

**Install:**

```bash
pip install ruff mypy

# or with poetry:
poetry add --group dev ruff mypy
```

---

## 2. Architecture & Dependency Direction (G01 — HARD)

See [python-dependency-direction.md](../../guides/architecture/examples/python-dependency-direction.md) for full reference.

**Summary:** `domain/`and`application/`must not import from`infrastructure/`or`adapters/`. Use `import-linter` to enforce in CI.

---

## 3. Anti-Patterns (G09 — HARD)

### Bare Except

```python

# VIOLATION
try:
    process()
except:
    pass

# OK
try:
    process()
except SpecificError as exc:
    raise ProcessingError("failed to process item") from exc
```

### Any-Driven Development

```python

# VIOLATION
def process(data: Any) -> Any:
    return data["key"]

# OK
def process(data: UserRequest) -> UserResponse:
    return UserResponse(id=data.user_id)
```

### Monkeypatch Architecture

Monkeypatching is for test doubles at real boundaries, not a substitute for dependency injection. If you need to patch 5 internal functions to test one function, the design has a problem.

### Import-Time Side Effects

```python

# VIOLATION — connects to DB at import time
import psycopg2
conn = psycopg2.connect(os.environ["DB_URL"])  # runs on import

# OK — explicit initialization
def create_connection(url: str) -> Connection:
    return psycopg2.connect(url)
```

---

## 4. Performance (G13 — SOFT)

**Measure first:**

```bash
python -m cProfile -o profile.out your_script.py
python -m pstats profile.out

# or with pytest-benchmark:
pytest --benchmark-only
```

**Key rules:**

- Avoid creating large lists when a generator suffices.

- Batch database calls — never N+1.

- Cache only when invalidation strategy is explicit (TTL or event-driven).

- Use `async`/`await` for I/O-bound work; never block the event loop with CPU work.

- Add benchmarks before and after non-trivial performance changes.

---

## 5. Project Structure (G17 — SOFT)

```
src/
  package_name/
    domain/          # business rules; zero framework imports
      models/
      services/
      ports/         # interfaces (output contracts)
    application/     # use cases; imports domain + ports only
      usecases/
    adapters/        # implements domain ports
      persistence/
      http/
      messaging/
    infrastructure/  # DI wiring, config, startup
  main.py            # composition root
tests/               # mirrors src/package_name/
  domain/
  application/
  adapters/
pyproject.toml
```

**Rules:**

- No `utils/`, `helpers/`, `common/` — name modules by business capability.

- Tests must mirror `src/` structure exactly.

- Use `src/` layout (not flat) to prevent import accidents.

---

## 6. CI Checklist

```bash
ruff check .              # linting
ruff format --check .     # formatting
mypy .                    # type checking
pytest                    # tests
import-linter             # architecture boundary check (see G01)
```
