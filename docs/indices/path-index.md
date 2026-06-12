# PATH Index

Maps task intents to the correct execution PATH. For detailed workflow per PATH, see [`AGENT_RUNTIME_PROTOCOL.md`](../runtime/protocols/AGENT_RUNTIME_PROTOCOL.md).

| Intent / Situation | PATH | Description |
|---|---|---|
| Fix an isolated bug | A | Bug fix — isolated change, <40KB context |
| Implement a simple feature (1-2 modules) | B | Simple feature — 1-2 affected layers, <45KB context |
| Implement a complex feature (cross-layer) | C | Complex feature — 3+ affected layers, <85KB context |
| Independent parallel work | D | Parallel work — independent sub-tasks, <35KB/thread |
| Production hotfix (urgent) | E | Production hotfix — urgent, prioritized over B & D |
| Refactoring / Tech Debt | F | Refactoring — structural, lowest priority |

---

## Routing Strategy

For task classification rules and routing logic, see:

- [`cognition/context-loading/path-routing.md`](../cognition/context-loading/path-routing.md) — Full routing table and decision heuristics
- [`cognition/decision-models/TASK_CLASSIFICATION.md`](../cognition/decision-models/TASK_CLASSIFICATION.md) — Classification rules
