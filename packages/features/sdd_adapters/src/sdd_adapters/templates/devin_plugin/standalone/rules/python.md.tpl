# Python

Ruleset version: `{{ standalone_ruleset_version }}`

## Code Style

**Tools:**

```bash
ruff check .
ruff format --check .
mypy .
```

**Rules:**

- All public functions and methods must have type annotations.
- No bare `except:` — always catch specific exceptions.
- No `Any` as a default type. Use `Protocol` for structural contracts.
- No import-time side effects (network I/O, global mutation, env reads at import).
- Use typed models (`dataclass`, `TypedDict`, a validated model type) for structured data.
- Inject dependencies via parameter — never via importing a module that carries global state.

## Architecture & Dependency Direction

Domain and application layers must not import from infrastructure or adapter layers. Enforce the boundary in CI with an import-linting tool.

## Anti-Patterns

**Bare except:**

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

**Any-driven development:**

```python
# VIOLATION
def process(data: Any) -> Any:
    return data["key"]


# OK
def process(data: UserRequest) -> UserResponse:
    return UserResponse(id=data.user_id)
```

**Import-time side effects:**

```python
# VIOLATION — connects to a database at import time
import psycopg2

conn = psycopg2.connect(os.environ["DB_URL"])  # runs on import


# OK — explicit initialization
def create_connection(url: str) -> Connection:
    return psycopg2.connect(url)
```

## Performance

- Avoid creating large lists when a generator suffices.
- Batch database calls — never N+1.
- Cache only when the invalidation strategy is explicit (TTL or event-driven).
- Use `async`/`await` for I/O-bound work; never block the event loop with CPU work.
- Add benchmarks before and after non-trivial performance changes.

## Project Structure

```
src/
  package_name/
    domain/          # business rules; zero framework imports
    application/      # use cases; imports domain only
    adapters/         # implements domain ports
    infrastructure/  # wiring, config, startup
  main.py
tests/               # mirrors src/package_name/
pyproject.toml
```

No `utils/`, `helpers/`, `common/` — name modules by business capability. Tests mirror `src/` structure exactly.

## CI Checklist

```bash
ruff check .
ruff format --check .
mypy .
pytest
```
