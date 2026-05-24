# Context Routing - PATH Selection

## Purpose
- Route work into PATH A-F with explicit context strategy and constraints.

## Routing Rules
- Active production incident -> PATH E.
- Isolated regression -> PATH A.
- Bounded feature with stable contracts -> PATH B.
- Multi-layer or architectural impact -> PATH C.
- Independent concurrent streams -> PATH D.
- Behavioral no-op structural cleanup -> PATH F.

## Per-PATH Load Strategy
- PATH A: affected layer + direct tests.
- PATH B: target modules + relevant guides.
- PATH C: canonical core + relevant decisions + integration tests.
- PATH D: isolated context per stream.
- PATH E: minimal failure surface and incident runbook.
- PATH F: scoped modules + pre/post behavior validation assets.

## Decision Heuristics
- Prefer smallest valid path, then escalate when evidence requires.
- Reclassify immediately on boundary breach.
- Keep a single active path per stream.

## Required Declaration
- Path selected.
- Reason for path.
- Estimated context budget.
- Reclassification trigger conditions.

## Related
- `docs/spec/canonical/core/cognition/decision-models/TASK_CLASSIFICATION.md`
- `docs/spec/canonical/core/cognition/context-loading/context-budget.md`
