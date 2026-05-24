# PATH D - Parallel Work

## Context Budget
- Per-stream isolation: each thread loads only its own required context.

## Scope
- 2+ independent work streams with no shared mutable state.

## Entry Checklist
- Enumerate streams and ownership.
- Validate no shared state between streams.

## MUST
- Classify each stream with its own PATH.
- Define integration order before execution.
- Validate isolation before merge.

## MUST NOT
- Share mutable state between streams.
- Merge incomplete streams.
- Add new streams without reclassification.

## Escalation
- Redesign as PATH C when streams share state.
- Switch affected stream to PATH E for urgent production incidents.
