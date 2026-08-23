# 🔌 RULESET — Dependencies

## 🎯 Purpose

Ensure low coupling and high testability.

---

## 🔒 HARD RULES

- Dependencies MUST be injected:
  - constructor OR
  - parameters

- Third-party libraries MUST be wrapped:
  - behind project-owned interfaces

---

## ❌ ANTI-PATTERNS

- global dependencies
- direct library calls across layers
