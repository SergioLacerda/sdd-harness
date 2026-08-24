# PATH E - Hotfix

## Context Budget

- Minimal: only production failure surface and immediate dependencies.

## Scope

- Minimum viable change to restore production availability.

## Entry Checklist

- Confirm active production impact.
- Identify smallest safe restoring action.

## MUST

- Apply minimal fix only.
- Document follow-up debt as PATH A.
- Validate no new critical failure mode introduced.

## MUST NOT

- Add features or refactor under emergency path.
- Treat hotfix as permanent resolution.
- Skip debt registration.

## Escalation

- Coordinate post-stabilization PATH C when deeper change is needed.
- Open PATH A immediately after production stabilizes.
