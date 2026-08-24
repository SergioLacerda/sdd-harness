# ⚠️ Heuristic Execution — Fallback Model

## 🎯 Purpose

Define controlled fallback behavior when no deterministic or guided pattern exists.

---

## ⚠️ Definition

Heuristic execution is:

> A last-resort decision strategy based on reasoning without explicit pattern support.

---

## 🔒 Rules

- MUST be used ONLY when:
  - no canonical rule exists
  - no guide exists
  - no prior pattern is available

- MUST be declared explicitly

---

## 🔁 Execution Flow

1. Attempt deterministic execution
2. Attempt guided execution
3. If both fail → heuristic mode allowed

---

## 🚨 Constraints

- MUST NOT override mandates
- MUST NOT bypass policies
- MUST NOT ignore runtime context

---

## 🧬 Required Declaration

Agent MUST emit:

```text
[HEURISTIC MODE]

Reason: No deterministic or guided pattern found
Risk Level: <low | medium | high>
```

---

## ⚠️ Anti-Patterns When Using Heuristics

- ❌ Using heuristics as default execution strategy
- ❌ Skipping context loading because "heuristics don't need it"
- ❌ Ignoring governance constraints under "flexibility" pretext
- ❌ Declaring heuristics without explicit reason

---

## 🎯 Goal

Allow controlled flexibility WITHOUT breaking system integrity.

Heuristics are for novel situations, not for bypassing rules.
