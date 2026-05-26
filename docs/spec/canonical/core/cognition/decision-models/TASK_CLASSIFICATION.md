# Decision Model - Task Classification

## Purpose

- Classify task type before loading broad context or writing code.

## Classification Tree

- Production broken now -> PATH E
- Previous behavior regressed -> PATH A
- Bounded to 1-2 files and no contract change -> PATH B
- Multi-layer impact or architectural decision -> PATH C
- Multiple independent streams without shared state -> PATH D
- Cleanup with zero behavior change -> PATH F

## Classification Rules

- Classify by impact, not effort.
- When uncertain between B and C, choose C.
- PATH E overrides all other paths.
- Do not combine PATH F and PATH B in one delivery.

## Progressive Task Decomposition

- PATH C must decompose into smaller executable units.
- If PATH B expands in-flight, halt and reclassify.
- Maximum decomposition depth is 3 before human checkpoint.
- Child tasks must retain traceability to parent work item.

## Reclassification Trigger

- Stop immediately when discovered scope exceeds declared path.
- Reclassify before continuing execution.

## Related

- `docs/spec/canonical/core/cognition/context-loading/path-routing.md`
- `docs/spec/canonical/core/cognition/context-loading/context-budget.md`
