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
