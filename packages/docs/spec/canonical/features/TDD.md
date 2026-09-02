# Mandate: Test-Driven Development (TDD)

**Type:** SELECTABLE MANDATE
**ID:** M002
**Category:** Testing / Quality

---

## 🎯 Goal

Ensure 100% functional coverage and design clarity by writing tests before implementation code.

---

## 📜 Requirement

All code changes must follow the **Red-Green-Refactor** cycle:

1. **Red**: Write a failing test for the new requirement.
2. **Green**: Write the minimal implementation to pass the test.
3. **Refactor**: Clean up the implementation while keeping the test green.

---

## ⚖️ Rationale

Ensures that the developer (or agent) is solving the right problem and that the solution is testable by design.

---

## ✅ Validation

- [ ] Test coverage ≥ 90% (or project-defined threshold).
- [ ] Git history shows test files created/modified before or alongside implementation files.
- [ ] `pytest --cov` passes with target metrics.

---

## Go Best-Practice Parameters (Governance)

When the target project language is Go, governance checks should validate:

- [ ] `go test ./...` is green for the changed scope before delivery.
- [ ] New behavior is introduced with test-first evidence (test added or updated before final implementation state).
- [ ] Table-driven tests are used for multi-scenario business rules where appropriate.
- [ ] Boundary contracts (ports/interfaces) have focused unit tests without external side effects.
- [ ] Race-sensitive changes run under `go test -race` in CI or pre-delivery gate when available.
