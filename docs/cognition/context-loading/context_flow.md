---
governance_source:
  id: HBK-CONTEXT-LOADING
  type: handbook
  kind: decision_model
  status: active
  title: Context Flow
  refs: [M003, M005]
  task_types: [planning, implementation, diagnosis]
  operation_phases: [context_loading, planning]
  load_policy:
    mode: selective
    max_tokens: 700
    require_relevance_reason: true
  summary: How agents route, prune, and pack relevant context before execution.
---

# 🧠 Context Flow — Token Optimization

```mermaid
flowchart TD

    %% Sources
    CANON[📚 CANONICAL\nRules / ADRs / Specs]
    REAL[🔍 REALITY\nCurrent state / issues]
    DEV[🟢 DEVELOPMENT\nActive work]
    AICTX[🧠 .sdd/context-aware\nSummaries / tasks]
    RUNTIME[⚡ .sdd/runtime\nIndexes / keywords]

    %% Query
    QUERY[🎯 Task Query\n"What am I doing?"]
    QUERY --> ROUTER

    %% Router
    ROUTER[🧭 Context Router\nSelect relevant docs only]

    CANON --> ROUTER
    REAL --> ROUTER
    DEV --> ROUTER
    AICTX --> ROUTER
    RUNTIME --> ROUTER

    %% Optimization
    ROUTER --> PRUNE[✂️ Pruning Engine\nRemove irrelevant content]
    PRUNE --> PACK[📦 Context Packing\nOptimize tokens]

    %% Agent
    PACK --> AGENT[🤖 Agent Input\nOptimized Context (~40–85KB)]

    %% Execution
    AGENT --> OUTPUT[💡 Execution / Code / Decisions]

    %% Feedback
    OUTPUT --> AICTX
    OUTPUT --> REAL

    %% CI feedback
    OUTPUT --> CI[⚖️ CI/CD Validation]
    CI --> CANON
```
