# PATH A - Bugfix

## Context Budget
- Narrow: affected module and directly connected tests only.

## Scope
- Root-cause fix for a regression or incorrect behavior.

## Entry Checklist
- Reproduce failure via test or concrete runtime evidence.
- Identify smallest change that restores expected behavior.

## MUST
- Fix root cause, not symptom masking.
- Add or update a regression test.
- Keep changes inside failure boundary.

## MUST NOT
- Include unrelated refactoring.
- Expand scope to adjacent issues.
- Close task without regression proof.

## Escalation
- Reclassify to PATH C when architecture must change.
- Reclassify to PATH C when 3+ modules are required.
