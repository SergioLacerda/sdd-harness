# 🔌 CONTRACTS — TEMPLATE

## 📌 PURPOSE

Define the interfaces (Ports) that connect the application to infrastructure.

All contracts MUST comply with:
- [Architecture Specification](./architecture.md)
- [Core Rules](../core/rules/)

---

## 🧩 PORT DEFINITION

### Example: Repository Port

```python
from typing import Protocol

class EntityRepositoryPort(Protocol):
    async def save(self, entity: "Entity") -> None:
        ...

    async def load(self, entity_id: str) -> "Entity | None":
        ...

    async def delete(self, entity_id: str) -> None:
        ...
```

---

## ⚙️ RULES

- Ports MUST be async
- Ports MUST define behavior, not implementation
- Ports MUST represent domain concepts
- Ports MUST NOT depend on infrastructure libraries

---

## ❌ PROHIBITED

- Concrete implementations
- Business logic inside ports
- External dependencies (e.g., chromadb, filesystem, etc.)

---

## 🔄 ADAPTER RESPONSIBILITY

Adapters MUST:

- Implement ports
- Handle serialization/deserialization
- Translate between domain and infrastructure

Adapters MUST NOT:

- Contain domain logic
- Be accessed directly outside repositories

---

## 🧪 VALIDATION

- Contracts MUST be testable
- Implementations MUST strictly follow contracts
- Async behavior MUST be enforced
