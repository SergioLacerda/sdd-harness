# Cognition — Index

This pillar defines **how the agent thinks**: how it classifies tasks, loads context, makes decisions, and avoids failure modes.

> Agents do not start here from a blank slate.
> Entry point is always: [`runtime/protocols/AGENT_ENTRYPOINT.md`](../runtime/protocols/AGENT_ENTRYPOINT.md)

---

## 🧠 Decision Models

Mental frameworks for making correct decisions before acting.

| Model | Purpose |
|---|---|
| [TASK_CLASSIFICATION.md](decision-models/TASK_CLASSIFICATION.md) | Which PATH to use for a given task |
| [IMPACT_ASSESSMENT.md](decision-models/IMPACT_ASSESSMENT.md) | Blast radius scoring before touching code |
| [CONFIDENCE_THRESHOLD.md](decision-models/CONFIDENCE_THRESHOLD.md) | When to proceed vs pause vs escalate |
| [GO_NO_GO_DECISION.md](decision-models/GO_NO_GO_DECISION.md) | Final commit gate: verification, governance, documentation |
| [KNOWLEDGE_GAP_QUIZ.md](decision-models/KNOWLEDGE_GAP_QUIZ.md) | Pre-implementation readiness: source/dependency/side-effect validation |

---

## 🔄 Context Loading

Strategy for loading only the relevant context per PATH.

| File | Purpose |
|---|---|
| [path-routing.md](context-loading/path-routing.md) | Full routing table: task → PATH → what to load |
| [context_flow.md](context-loading/context_flow.md) | Visual flowchart of the context loading mechanism |
| [CONTEXT_BUDGET.md](context-loading/CONTEXT_BUDGET.md) | Token economy and reasoning space management |
| [CONTEXT_POISONING.md](context-loading/CONTEXT_POISONING.md) | Conflict and stale doc prevention |
| [CONTEXT_VERIFICATION.md](context-loading/CONTEXT_VERIFICATION.md) | Pre-flight context sufficiency check |

---

## ❌ Anti-Patterns

Common failure modes with diagnosis and cure.

| Anti-Pattern | Description |
|---|---|
| [COGNITIVE_OVERLOAD.md](anti-patterns/COGNITIVE_OVERLOAD.md) | Loading too much context, losing focus |
| [SCOPE_CREEP.md](anti-patterns/SCOPE_CREEP.md) | Expanding scope during execution |
| [PREMATURE_EXECUTION.md](anti-patterns/PREMATURE_EXECUTION.md) | Implementing before defining "done" |
| [SYMPTOM_FIXING.md](anti-patterns/SYMPTOM_FIXING.md) | Fixing symptoms instead of root causes |
| [RESOLUTION_BYPASS.md](anti-patterns/RESOLUTION_BYPASS.md) | Hacking dependency resolution at runtime |
