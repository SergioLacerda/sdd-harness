# PATH B - Simple Feature

## Context Budget
- Narrow: 1-2 target files plus direct tests.

## Scope
- Bounded feature with no public API contract changes.

## Entry Checklist
- Confirm change fits within 1-2 files.
- Confirm no cross-domain side effects.

## MUST
- Add tests for new behavior.
- Keep implementation within declared boundary.
- Preserve existing contracts.

## MUST NOT
- Touch unrelated files opportunistically.
- Change public API contracts.
- Mix refactor and feature in same delivery.

## Escalation
- Reclassify to PATH C when scope exceeds 2 files.
- Reclassify to PATH C when contract changes are required.
