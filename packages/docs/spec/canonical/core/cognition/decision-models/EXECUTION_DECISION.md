# 🧠 Decision Model — Execution Strategy

## 🎯 Purpose

Define how the agent decides HOW to execute a task after context is loaded.

---

## 🔁 Decision Flow

1. Validate handshake (runtime loaded)
2. Confirm task classification
3. Select execution path (A/B/C/D)
4. Determine scope:
   - single-layer
   - multi-layer
   - cross-cutting

---

## 🔀 Execution Modes

| Mode | Description |
|------|------------|
| Deterministic | Strict rules + known pattern |
| Guided | Use guides + patterns |
| Exploratory | When no pattern exists |

---

## 🔒 Rules

- MUST prefer deterministic execution
- MUST fallback to guided before exploratory

---

## ⚖️ Decision Criteria

- Complexity of task
- Number of layers affected
- Availability of patterns
- Risk level

---

## 🚨 Anti-Patterns

- Starting execution before classification
- Mixing multiple execution strategies
- Ignoring governance constraints

---

## 🧬 Output

Agent MUST define:

- execution mode
- path selected
- scope of change
