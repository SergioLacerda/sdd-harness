# Mandate: Clean Architecture

**Type:** SELECTABLE MANDATE
**ID:** M001
**Category:** Architecture

---

## 🎯 Goal

Ensure maintainability and testability by separating concerns into distinct, independent layers.

---

## 📜 Requirement

All systems must implement the **8-layer Clean Architecture** pattern:

1. Domain (Entities)
2. Use Cases (Interactors)
3. Ports (Interfaces)
4. Adapters (Gateways/Controllers)
5. Infrastructure
6. External Services
7. UI/CLI
8. Configuration/Composition Root

---

## ⚖️ Rationale

Prevents business logic from leaking into framework-specific code, enabling easy replacement of databases, UI, or external APIs.

---

## ✅ Validation

- [ ] Directory structure follows the 8-layer model.
- [ ] Dependency flow is unidirectional (inner circles don't know about outer circles).
- [ ] Domain logic has zero dependencies on external libraries.
