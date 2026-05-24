# Mandate: Context Awareness & Task Caching

**Type:** HARD MANDATE
**ID:** M003
**Category:** Cognition / Operational Efficiency / Context

---

## 🎯 Goal
Ensure absolute continuity of state and logic across parallel agents, long-running tasks, and multi-repository environments by maintaining a persistent, project-isolated "Context Cache".

---

## 📜 Requirement

1. **Mandatory Cache File**: Every project must maintain a `.sdd-cache.md` (or `.sdd/task-context.json`) in its root.
2. **Sub-task Checkpoint**: Agents MUST update this cache at the end of EVERY sub-task or significant logical block.
3. **Pre-flight Sync**: Before starting any task, the agent MUST read the cache to synchronize with the current global state of the project, overriding stale memory.
4. **Isolation**: The cache is strictly project-scoped. In multi-repository IDEs, agents must treat each repository as a separate context-aware cell.

---

## 🛠️ Implementation Pattern

### The Cache Structure (World-Class)

The cache must contain:
- **Current Objective**: The high-level goal being pursued.
- **Active Sub-task**: What is being worked on *right now*.
- **Completed Milestones**: List of what is 100% verified.
- **Shared Variables/States**: Key architectural or runtime values that multiple agents need to know.
- **Pending Risks**: Blockers or "Gotchas" discovered during execution.

### Example Update Workflow
```bash
# At the end of a subtask:
1. Validate subtask completion (tests pass).
2. Write summary to .sdd-cache.md.
3. Commit cache alongside code changes.
```

---

## ⚖️ Rationale
- **Parallelism**: Prevents Agent A from breaking assumptions made by Agent B.
- **Context Longevity**: Prevents "forgetting" the main goal when the token window fills up with implementation details.
- **Multi-Repo Safety**: Ensures the agent doesn't mix up rules between two different projects open in the same workspace.

---

## ✅ Validation
- [ ] Presence of `.sdd-cache.md` in root.
- [ ] Git history shows cache updates synchronized with logical feature commits.
- [ ] Cache content reflects the actual current state of the implementation.

---

## Skill-Oriented Reinforcement (Normative)

- [ ] When a capability-oriented skill exists for the task, agents SHOULD prefer `sdd skills run <skill>` over ad-hoc command guessing.
- [ ] If no suitable skill exists, agents MAY fall back to low-level CLI primitives with explicit context synchronization first.
- [ ] The selected execution mode (skill or primitive fallback) MUST be recorded in session context for downstream auditability.

---

## References
- Agent Entry Point: [`generated/AGENT_ENTRYPOINT.md`](../generated/AGENT_ENTRYPOINT.md)
- Context Budgeting: [`cognition/context-loading/context-budget.md`](../cognition/context-loading/context-budget.md)
- Onboarding Metrics: [`onboarding/metrics.md`](../onboarding/metrics.md)
