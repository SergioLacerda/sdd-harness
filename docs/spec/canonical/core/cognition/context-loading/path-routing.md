# 🧠 Context Routing — PATH Selection

## 🎯 Purpose

Route tasks into predefined execution paths based on task type, scope, and complexity.

---

## 🔀 Execution Paths

### PATH A — Bug Fix
- **Scope:** Isolated change
- **Layers Affected:** 1
- **Context Budget:** ~40KB / 17K tokens
- **Characteristics:** Single file, single function, no cross-module effects
- **When to use:** "Fix this specific bug in isolation"

### PATH B — Simple Feature
- **Scope:** Limited scope
- **Layers Affected:** 1–2
- **Context Budget:** ~45KB / 21K tokens
- **Characteristics:** One or two modules, minimal cross-layer dependencies
- **When to use:** "Add a simple feature to 1-2 modules"

### PATH C — Complex Feature
- **Scope:** Multi-layer
- **Layers Affected:** 3+
- **Context Budget:** ~85KB / 35K tokens
- **Characteristics:** Cross-module, cross-layer dependencies
- **When to use:** "Major feature affecting multiple layers"

### PATH D — Parallel Work
- **Scope:** Independent tasks run in parallel
- **Layers Affected:** Per thread: 1–2
- **Context Budget:** ~35KB / 15K tokens **per thread**
- **Characteristics:** Multiple independent sub-tasks, no inter-task dependencies
- **When to use:** "Multiple independent work items"

### PATH E — Production Hotfix
- **Scope:** Urgent production issue
- **Layers Affected:** 1–2
- **Context Budget:** Minimal / 10K tokens (efficiency critical)
- **Characteristics:** Fast path, minimal validation, human review required
- **When to use:** "Production is down, fix now"
- **Note:** Overrides PATH B and D priority

### PATH F — Refactoring
- **Scope:** Structural, no behavior change
- **Layers Affected:** 1–3
- **Context Budget:** Same as feature (45–85KB)
- **Characteristics:** Code quality, tech debt, architecture
- **When to use:** "Improve structure without changing behavior"
- **Note:** Lowest priority (run after A, B, C, E)

---

## 🔁 PATH Selection Rules

Agent MUST follow this logic:

1. **Is it urgent (production down)?** → Use PATH E
2. **Is it a bug fix?** → Use PATH A
3. **Will it affect 1–2 modules?** → Use PATH B
4. **Will it affect 3+ modules/layers?** → Use PATH C
5. **Are there multiple independent sub-tasks?** → Use PATH D
6. **Is it only structure/refactoring?** → Use PATH F

---

## ⚖️ Decision Table

| Task Description | Path | Context | Reason |
|---|---|---|---|
| Single bug in one function | A | ~40KB | Isolated scope |
| Add feature to 1-2 modules | B | ~45KB | Limited cross-module impact |
| Cross-layer feature (3+ modules) | C | ~85KB | Full context for coordination |
| Multiple parallel independent tasks | D | ~35KB/thread | Per-thread isolation |
| Production incident (urgent) | E | ~10KB | Speed critical |
| Code refactoring (no behavior change) | F | ~45-85KB | Structure changes |

---

## 🚨 Anti-Patterns

| ❌ Anti-Pattern | ✅ Fix |
|---|---|
| Using PATH C for simple 1-module changes | Use PATH A or B for isolation |
| Mixing multiple paths in one task | Select ONE path, stick to it |
| Ignoring path budget constraints | Check context % before proceeding |
| Downgrading PATH E to B "to save time" | Never — hotfixes stay PATH E |
| Using PATH D without .sdd-cache.md sync | Always update cache between threads |

---

## 🧬 Required PATH Declaration

Agent MUST declare before execution:

```text
[PATH SELECTION]
Path: <A | B | C | D | E | F>
Reason: <why this path was chosen>
Context Budget: <estimated KB>
Estimated Token Usage: <~X tokens>
```

Example:
```text
[PATH SELECTION]
Path: B
Reason: Simple feature affecting UserService and validation layer (2 modules)
Context Budget: 45KB
Estimated Token Usage: ~21K tokens
```

---

## 🔗 Related

- [TASK_CLASSIFICATION.md](../decision-models/TASK_CLASSIFICATION.md) — Detailed classification rules
- [context-budget.md](./context-budget.md) — Budget targets and compression
- [AGENT_RUNTIME_PROTOCOL.md](../../../generated/AGENT_RUNTIME_PROTOCOL.md) — PATH usage in execution flow
