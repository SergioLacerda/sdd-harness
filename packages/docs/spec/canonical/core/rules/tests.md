# 🧪 RULESET — Tests

## 🎯 Purpose

Guarantee reliability and regression safety.

---

## 🔒 HARD RULES

- Tests MUST run with a single command

- Every new function MUST have a test

- Every bug fix MUST include a regression test

- Tests MUST follow F.I.R.S.T:
  - Fast
  - Independent
  - Repeatable
  - Self-validating
  - Timely

---

## 🔧 IMPLEMENTATION

- External I/O MUST be mocked

- Mocks MUST:
  - use named fake classes
  - ❌ NOT inline stubs

---

## ❌ ANTI-PATTERNS

- tests hitting real APIs
- missing regression coverage
