# PATH C - Complex Feature

## Context Budget
- Broad: affected domain layers, contracts, and cross-layer tests.

## Scope
- Multi-layer change or architectural decision requiring explicit design control.

## Entry Checklist
- Confirm approved plan/spec before implementation.
- Identify impacted interfaces and dependencies upfront.

## MUST
- Keep requirements/design traceable to implementation.
- Validate behavior across all touched layers.
- Record architectural decisions in canonical decision docs.

## MUST NOT
- Start coding without approved scope.
- Hide architectural change under simple-feature path.
- Combine with PATH F in same delivery.

## Escalation
- Split independent streams into PATH D.
- Pause and switch to PATH E if production emergency appears.
