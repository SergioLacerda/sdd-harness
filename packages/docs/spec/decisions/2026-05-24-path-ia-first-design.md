# PATH A-F Differentiation + IA First Authoring Standard

**Date:** 2026-05-24
**Status:** Approved

## Problem

`PATH_A_BUGFIX.md` through `PATH_F_REFACTOR.md` contain identical content (874 bytes each).
The cognitive constraints, scope limits, and decision rules that make each execution path
distinct are missing. Agents routed here by `TASK_CLASSIFICATION.md` receive no useful
guidance specific to their task type.

Additionally, no authoring standard exists for runtime docs — leading to inconsistent
structure, variable verbosity, and unpredictable token cost for agents loading them.

## Goals

- Each PATH file must encode constraints unique to its execution type.
- All PATH files must share a fixed, machine-parseable section schema (same sections, same order).
- Introduce `IA_FIRST.md` as the authoring standard for all runtime docs.
- Human readability is preserved; agent token economy is the primary constraint.

## Non-Goals

- Rewriting non-runtime docs (guides, ADRs, specs) under the IA First standard.
- Changing `TASK_CLASSIFICATION.md` — it is the correct routing entry point.
- Adding prose explanations inside PATH files.

## IA First Authoring Standard

### Definition

IA First means: the agent is the primary consumer. The document is structured so the
agent can locate any section without reading the file sequentially.

### Rules

1. Fixed section schema: every doc in the same family has the same sections in the same order.
2. No section exceeds 5 items. If 6+ items exist, the concept needs decomposition.
3. Lists over prose. A sentence that can be a bullet must be a bullet.
4. Every runtime doc declares a `## Context Budget` — explicit token exploration scope.
5. Cross-references use exact filenames, never prose descriptions.

### Schema for PATH family

```
# PATH {X} — {LABEL}

## Context Budget
## Scope
## Entry Checklist
## MUST
## MUST NOT
## Escalation
```

This order is fixed. Agents parse by section header; order determines load priority.

---

## PATH Differentiation Design

### PATH A — Bugfix

**Context Budget:** Narrow — load only affected module + directly connected tests.

**Scope:** Root cause of the regression. Nothing outside the failure boundary.

**Entry Checklist:**

- Reproduce the failure with a failing test or log evidence.
- Identify the smallest change that restores correct behavior.

**MUST:**

- Fix the root cause, not the symptom.
- Add or update a regression test covering the fixed path.
- Stay within the declared failure boundary.

**MUST NOT:**

- Refactor while fixing.
- Expand scope to "nearby" issues found during investigation.
- Mark done without a passing regression test.

**Escalation:**

- Root cause is architectural → reclassify to PATH C.
- Fix requires touching 3+ modules → reclassify to PATH C.

---

### PATH B — Simple Feature

**Context Budget:** Narrow — load 1-2 target files + their direct test files.

**Scope:** Bounded to 1-2 files. No public API contract changes. No architectural decisions.

**Entry Checklist:**

- Confirm scope fits 1-2 files.
- Confirm no API surface changes.
- Confirm no cross-domain side effects.

**MUST:**

- Write tests for the new behavior.
- Keep changes within declared file boundary.

**MUST NOT:**

- Touch unrelated files "while you're in there."
- Make API contract changes (escalate to PATH C instead).
- Mix refactoring with the feature (run PATH F separately).

**Escalation:**

- Scope exceeds 2 files → reclassify to PATH C.
- API contract changes needed → reclassify to PATH C.

---

### PATH C — Complex Feature

**Context Budget:** Broad — load all affected domain layers + contracts + tests.

**Scope:** Multi-layer changes or architectural decisions. Full design cycle required.

**Entry Checklist:**

- Brainstorming + spec written and approved before any code.
- ADR created if an architectural decision is made.
- Impacted contracts and interfaces identified upfront.

**MUST:**

- Complete spec before implementation (ADR-007).
- Document every architectural decision in an ADR.
- Full test coverage across all touched layers.

**MUST NOT:**

- Start coding before spec is approved.
- Combine with PATH F (refactor) in the same delivery.
- Understate scope to avoid the spec requirement.

**Escalation:**

- Scope splits into independent streams → spawn PATH D.
- Production emergency discovered mid-execution → pause, switch to PATH E.

---

### PATH D — Parallel Work

**Context Budget:** Per stream — each stream loads its own narrow context independently.

**Scope:** 2+ independent work streams with no shared mutable state.

**Entry Checklist:**

- Enumerate all streams and confirm they share no state.
- Classify each stream independently (PATH A, B, C, or F).
- Define merge strategy before starting any stream.

**MUST:**

- Treat each stream as its own PATH execution.
- Define integration point and merge order upfront.
- Validate isolation — streams must not introduce shared side effects.

**MUST NOT:**

- Let streams share mutable state.
- Merge before each stream has passed its own PATH validation.
- Add a stream mid-execution without reclassifying.

**Escalation:**

- Streams discovered to share state → stop, redesign as PATH C.
- One stream becomes a production emergency → that stream switches to PATH E.

---

### PATH E — Hotfix

**Context Budget:** Minimum — load only the production failure surface.

**Scope:** Minimum viable fix to restore production. Zero scope addition permitted.

**Entry Checklist:**

- Confirm production is broken right now.
- Identify the smallest change that restores service.
- Document the technical debt this fix creates.

**MUST:**

- Apply minimum viable fix only.
- Document debt created (file a PATH A follow-up immediately).
- Confirm fix does not introduce new failure modes.

**MUST NOT:**

- Add features, refactors, or "improvements" under hotfix cover.
- Skip debt documentation.
- Treat PATH E as a permanent fix — it is always followed by PATH A.

**Escalation:**

- Fix requires multi-layer changes → PATH E still applies, but coordinate with PATH C post-stabilization.
- Production stabilized → immediately open PATH A for root cause work.

---

### PATH F — Refactor

**Context Budget:** Narrow — load declared modules only.

**Scope:** Zero behavior change. Code quality improvement only.

**Entry Checklist:**

- Full test suite passes before any change.
- Declared scope: list of modules being refactored.
- Confirm no new features are included.

**MUST:**

- Test suite passes before and after with identical behavior.
- Stay within declared module scope.
- Commit refactor separately from any feature work.

**MUST NOT:**

- Change observable behavior (inputs → outputs must be identical).
- Mix with PATH B or PATH C in the same delivery.
- Expand scope based on findings during refactor.

**Escalation:**

- Behavior change required to improve the code → reclassify to PATH B or PATH C.
- Scope exceeds declared modules → stop, re-declare scope, restart.

---

## New File: `docs/runtime/IA_FIRST.md`

Defines the IA First authoring standard. Referenced in the header of every PATH file
and in the `docs/runtime/` README. This file itself follows the IA First standard.

---

## Files Affected

| File | Change |
|---|---|
| `docs/runtime/paths/PATH_A_BUGFIX.md` | Replace with differentiated content |
| `docs/runtime/paths/PATH_B_SIMPLE_FEATURE.md` | Replace with differentiated content |
| `docs/runtime/paths/PATH_C_COMPLEX_FEATURE.md` | Replace with differentiated content |
| `docs/runtime/paths/PATH_D_PARALLEL_WORK.md` | Replace with differentiated content |
| `docs/runtime/paths/PATH_E_HOTFIX.md` | Replace with differentiated content |
| `docs/runtime/paths/PATH_F_REFACTOR.md` | Replace with differentiated content |
| `docs/runtime/IA_FIRST.md` | New file — authoring standard |

## Acceptance Criteria

1. All 6 PATH files have distinct content matching their execution type.
2. All 6 PATH files share the same 6-section schema in the same order.
3. No PATH file section exceeds 5 items.
4. `IA_FIRST.md` exists and defines the authoring standard.
5. `TASK_CLASSIFICATION.md` references `IA_FIRST.md` (or vice versa) for discoverability.
