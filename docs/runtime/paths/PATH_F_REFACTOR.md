# PATH F - Refactor

## Context Budget
- Narrow: declared refactor modules and their current tests.

## Scope
- Structural/code-quality improvement with zero behavior change.

## Entry Checklist
- Capture baseline test status before edits.
- Declare exact module scope.

## MUST
- Keep observable behavior identical.
- Keep before/after test outcomes equivalent.
- Deliver refactor separately from feature changes.

## MUST NOT
- Change product behavior.
- Mix with PATH B or PATH C in same delivery.
- Expand scope ad hoc during execution.

## Escalation
- Reclassify to PATH B/C if behavior change becomes required.
- Stop and rescope when module boundary is exceeded.
