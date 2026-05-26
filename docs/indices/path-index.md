# PATH Index

Maps task intents to the correct execution PATH. For detailed workflow per PATH, see [`AGENT_RUNTIME_PROTOCOL.md`](../runtime/protocols/AGENT_RUNTIME_PROTOCOL.md).

| Intent / Situação | PATH | Descrição |
|---|---|---|
| Corrigir um bug isolado | A | Bug fix — isolated change, <40KB context |
| Implementar feature simples (1-2 módulos) | B | Simple feature — 1-2 affected layers, <45KB context |
| Implementar feature complexa (cross-layer) | C | Complex feature — 3+ affected layers, <85KB context |
| Trabalhos paralelos independentes | D | Parallel work — independent sub-tasks, <35KB/thread |
| Hotfix de produção (urgente) | E | Production hotfix — urgent, prioritized over B & D |
| Refatoração / Tech Debt | F | Refactoring — structural, lowest priority |

---

## Estratégia de Roteamento

For task classification rules and routing logic, see:

- [`cognition/context-loading/path-routing.md`](../cognition/context-loading/path-routing.md) — Full routing table and decision heuristics
- [`cognition/decision-models/TASK_CLASSIFICATION.md`](../cognition/decision-models/TASK_CLASSIFICATION.md) — Classification rules
