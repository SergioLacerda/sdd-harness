# Example: Dependency Direction — Python (adapts M001)

**Guideline ID:** G01 (sequential; see `guidelines.dsl`)
**Canonical mandate:** M001 — Clean Architecture
**Language:** Python

---

## DSL Entry

```
guideline G01 {
  type: HARD
  title: "Dependency Direction — Python"
  description: "Domain and application layers must not import infrastructure adapters or framework code directly. Use import-linter to enforce boundaries."
  category: architecture
  mandate_ref: M001
  tags: ["python", "import-linter", "ruff"]
  enforcement: {
    gate: ci
    severity: block
    tools: ["ruff check .", "mypy .", "python -m importchecker"]
  }
  violations: ["domain_imports_infrastructure", "app_imports_concrete_adapter", "framework_leaks_into_domain", "config_or_env_read_inside_domain"]
  exception_policy: {
    requires: ["diagnosis", "evidence", "temporary_marker", "follow_up_task"]
    ttl: sprint
  }
  maturity_level: 2
  examples: ["from src.infrastructure.db import Session  # in domain/ → VIOLATION", "class UserRepo(Protocol): ...  # in src/ports/ → OK"]
}
```

---

## Violation Patterns

### `domain_imports_infrastructure`

```python
# src/domain/user_service.py — VIOLATION
from src.infrastructure.postgres import PostgresUserRepo  # ← breaks direction
```

**Why it matters:** domain logic now depends on a concrete adapter. Swapping
PostgreSQL for a different backend requires changes inside the domain.

**Correct pattern:**

```python
# src/domain/user_service.py — OK
from src.ports.user_repository import UserRepository  # protocol/interface only
```

### `app_imports_concrete_adapter`

```python
# src/application/create_user.py — VIOLATION
from src.infrastructure.http_client import HttpNotifier  # ← concrete adapter
```

**Correct pattern:**

```python
# src/application/create_user.py — OK
from src.ports.notifier import Notifier  # inject via DI
```

### `config_or_env_read_inside_domain`

```python
# src/domain/pricing.py — VIOLATION
import os

TAX_RATE = float(os.environ["TAX_RATE"])  # ← infra concern in domain
```

**Correct pattern:**

```python
# src/domain/pricing.py — OK
def calculate_price(amount: float, tax_rate: float) -> float:
    return amount * (1 + tax_rate)  # injected, not read from env
```

---

## Exception Example (M016 compliant)

```python
# src/domain/legacy_adapter.py
from src.infrastructure.legacy_orm import LegacyModel  # type: ignore[import]

# noqa: DOMAIN_IMPORTS_INFRA

# diagnosis: LegacyModel predates ports layer; full migration blocked by Q3 freeze

# evidence: https://github.com/org/repo/issues/4231

# follow_up: issue #4231 — remove before v4.0
```

---

## Tooling Setup

**`import-linter` config (`.importlinter`):**

```ini
[importlinter]
root_package = src

[importlinter:contract:domain-independence]
name = Domain must not import infrastructure
type = forbidden
source_modules =
    src.domain
    src.application
forbidden_modules =
    src.infrastructure
    src.adapters
```

**CI check:**

```bash
ruff check .
mypy src/
python -m importchecker
```
