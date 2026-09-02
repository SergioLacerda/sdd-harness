# Rules: Code Style

Hard rules for naming, organization, and code formatting.

---

## Naming Conventions

### Classes

- **MUST** use PascalCase: `UserRepository`, `CampaignUseCase`
- **MUST** be singular nouns: ❌ `Users` → ✅ `User`
- **MUST** include domain concept in name: `UserEntity`, `CampaignRepository`
- **Port classes:** Suffix with `Port`: `RepositoryPort`, `NotificationPort`
- **Adapter classes:** Suffix with `Adapter`: `PostgresAdapter`, `FileSystemAdapter`

### Functions & Methods

- **MUST** use snake_case: `get_user_by_id()`, `save_campaign()`
- **MUST** be verb phrases: `get_`, `create_`, `update_`, `delete_`, `save_`, `load_`
- **MUST NOT** abbreviate: ❌ `get_usr_id()` → ✅ `get_user_id()`
- **Private methods:** Prefix with `_`: `_validate_input()`, `_transform_data()`
- **Async methods:** No suffix needed, but type hint with `async def`

### Variables & Constants

- **Variables:** snake_case: `user_id`, `campaign_data`, `vector_index`
- **Constants:** UPPERCASE: `MAX_RETRIES`, `DEFAULT_TIMEOUT`, `VECTOR_DIMENSION`
- **MUST** be descriptive: ❌ `x`, `tmp`, `data` → ✅ `vector_embedding`, `temp_cache`
- **Boolean variables:** Prefix with `is_`, `has_`, `can_`: `is_active`, `has_permissions`, `can_merge`

### Files & Modules

- **MUST** use snake_case: `campaign_repository.py`, `user_service.py`
- **MUST** match primary class: `user_repository.py` contains class `UserRepository`
- **Tests:** Suffix with `_test.py`: `campaign_repository_test.py`
- **Directories:** snake_case, plural for collections: `repositories/`, `use_cases/`, `adapters/`

---

## Code Organization

### Module Imports

```python
# Order:
# 1. Standard library
# 2. Third-party
# 3. Domain/Application (. or ..)
# 4. Infrastructure

from typing import Protocol
import asyncio

from pydantic import BaseModel
from sqlalchemy import Column, String

from domain.campaign import Campaign
from application.ports import RepositoryPort

from infrastructure.adapters.postgres import PostgresConnection
```

### Class Organization

```python
class MyClass:
    """Docstring."""

    # 1. Class variables
    # 2. __init__
    # 3. Public methods
    # 4. Private methods (prefix with _)
    # 5. Async methods (group by type)
```

---

## Formatting

- **Line length:** 88 characters (Black formatter default)
- **Indentation:** 4 spaces (never tabs)
- **Blank lines:** 2 lines between top-level definitions, 1 between methods
- **Use ruff & mypy:** Enforce via CI/CD (see `make lint`)

---

## Documentation

- **Docstrings:** Required for public classes/methods (not internal methods)
- **Format:** Google-style docstrings
- **Comments:** Explain WHY, not WHAT (code already explains what)
- **Type hints:** MUST include for all function signatures

---

## Common Violations

| ❌ Anti-Pattern | ✅ Fix |
|---|---|
| `x`, `tmp_var`, `data` | `user_id`, `temp_cache`, `campaign_data` |
| `UserS` (plural class) | `User` (singular) |
| `GetUserID()` (camelCase function) | `get_user_id()` (snake_case) |
| Hardcoded values | Use constants with UPPERCASE names |
| Mixed import order | Follow defined order (stdlib → 3rd-party → local) |
| Magic numbers | Extract to named constants |

---

## Validation

Enforced via:

- ✅ `ruff check` — Linting and style violations
- ✅ `mypy` — Type checking
- ✅ `black --check` — Line length and formatting (if configured)
- ✅ `make lint` — All style checks combined
- ✅ `make pre-delivery` — P004 Pre-Delivery Quality Gate includes lint
