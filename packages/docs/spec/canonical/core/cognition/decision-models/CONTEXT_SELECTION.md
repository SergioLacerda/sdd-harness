# 🧠 Decision Model — Context Selection

## 🎯 Purpose

Define how the agent selects the MINIMAL required context to execute a task.

---

## 🔒 Core Principle

> Load ONLY what is necessary. Never load everything.

---

## 🔁 Decision Flow

1. Classify task (see TASK_CLASSIFICATION)
2. Identify affected domain:
   - API
   - Persistence
   - Domain logic
   - UI
   - Infra

3. Map domain → required docs

4. Load ONLY:
   - relevant canonical specs
   - path-specific guides
   - runtime indices

---

## 📦 Context Types

| Type | Description |
|------|------------|
| Canonical | Rules, contracts, architecture |
| Guides | Execution patterns |
| Runtime | Indices, current state |
| Reality | Known issues, constraints |

---

## ⚖️ Selection Rules

- MUST prioritize:
  - canonical over guides
  - guides over assumptions

- MUST avoid:
  - loading unrelated domains
  - loading entire spec tree

---

## 🚨 Anti-Patterns

- Loading entire `/docs/spec/`
- Ignoring indices
- Using memory instead of runtime context

---

## 🧬 Output

Agent MUST know:

- what was loaded
- why it was loaded
- what was intentionally ignored
