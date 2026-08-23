# Mandate: Code Quality Baseline

**ID:** M018
**Type:** MANDATE
**Enforcement:** HARD
**Required:** true
**Phase:** post-execution

---

## Objective

Enforce a universal code quality baseline across all language implementations
to ensure consistency, maintainability, and correctness of engineering artifacts.
Language-specific enforcement is delegated to guideline entries (G-series) that
reference this mandate.

---

## Requirements

1. All code must pass the language-appropriate linter and formatter before delivery.
2. All code must pass static type checking where a type checker is available.
3. All code must pass the full test suite before delivery.
4. Code quality tools must be run in auto-fix mode first, then revalidated.

---

## Enforcement Steps

- Confirm language-appropriate linter was executed and passes
- Confirm formatter was executed and passes
- Confirm static type checker was executed and passes (if available)
- Confirm test suite was executed and passes

---

## Rationale

A consistent code quality baseline prevents style drift, type errors, and
regressions from reaching reviewers. Language-specific guidelines (G-series)
extend this mandate with toolchain-specific enforcement rules without
duplicating the core quality contract.
