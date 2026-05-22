# PATH A

## Cognitive Objective

Minimize exploration breadth while preserving deterministic convergence for this path.

## Scope

- Restrict execution to affected modules and directly connected tests.
- Expand context only with explicit evidence.

## MUST

- Start with smallest meaningful validation.
- Keep changes within declared path intent.
- Document deviations when path escalation is required.

## MUST NOT

- Run broad refactors outside scoped objective.
- Execute full-suite retries without new evidence.
- Mix unrelated tasks in the same path execution.

## INVALID

- Any execution that changes architectural scope without path reclassification.
- Any retry loop without new diagnostics.

## Escalation/Recovery

- If convergence stalls, reclassify task using TASK_CLASSIFICATION.
- If risk crosses path boundaries, escalate to PATH C with explicit rationale.
