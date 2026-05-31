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

---

## Go Best-Practice Parameters (Governance)

When the target project language is Go, governance checks should validate:

- [ ] Domain and application packages do not import infrastructure adapters directly.
- [ ] Use constructor-based dependency injection with interfaces at boundaries (ports).
- [ ] Keep business rules in `internal/domain` and orchestration in `internal/app` (or equivalent).
- [ ] Avoid framework/runtime coupling in domain packages (`net/http`, DB drivers, SDKs in outer layers only).
- [ ] Composition root wires concrete adapters in outer layer (`cmd/*` or dedicated bootstrap package).
