# 🧠 Context Budget

## 🎯 Purpose

Control how much context the agent loads to optimize token usage.

---

## 🔒 Core Principle

> More context ≠ better results

---

## 📊 Budget Targets

| Scenario | Target |
|----------|--------|
| Bug Fix | ~40KB |
| Simple Feature | ~45KB |
| Complex Feature | ~85KB |
| Multi-thread | ~35KB per thread |

---

## 🔁 Budget Strategy

1. Load indices (~5KB)
2. Load minimal canonical (~20–30KB)
3. Load guides if needed (~10–20KB)

---

## ⚖️ Constraints

- MUST stay within target range
- MUST avoid unnecessary documents

---

## 🚨 Anti-Patterns

- Loading entire canonical
- Loading all guides
- Ignoring budget limits

---

## 📉 Optimization Techniques

- Use indices instead of full docs
- Prefer summaries over full files
- Load incrementally

---

## 🧬 Outcome

- faster execution
- lower token cost
- higher signal density
