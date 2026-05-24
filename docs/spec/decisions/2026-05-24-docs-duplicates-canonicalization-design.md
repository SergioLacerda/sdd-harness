# Docs Duplicates Canonicalization

**Date:** 2026-05-24
**Status:** Approved

## Problem

22 files across 8 naming patterns appear in multiple locations. Inspection reveals three
distinct situations requiring different treatments. A blanket "keep one, delete the rest"
approach would destroy content with unique value.

## Canonical Layer Definitions

| Location | Role |
|---|---|
| `spec/canonical/` | Immutable core — non-negotiable governance and definitions |
| `runtime/` | Operational instructions for agents during task execution |
| `cognition/` | Agent learning, discernment, and convergence material |

These layers serve different purposes and are NOT duplicates of each other when content differs.

---

## Three Situations, Three Treatments

### Situation 1 — True Stubs (remove)

`docs/runtime/AGENT_ENTRYPOINT.md` and `docs/runtime/AGENT_RUNTIME_PROTOCOL.md` are
explicit stubs pointing to `docs/runtime/protocols/`. They contain no content of their own.

**Treatment:** Delete both stub files. Update all internal links that reference them to
point directly to `docs/runtime/protocols/AGENT_ENTRYPOINT.md` and
`docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md`.

Files removed:
- `docs/runtime/AGENT_ENTRYPOINT.md`
- `docs/runtime/AGENT_RUNTIME_PROTOCOL.md`

---

### Situation 2 — Complementary Content Requiring Merge

`docs/cognition/` and `docs/spec/canonical/core/cognition/` cover the same topics
but from different angles:

| File | `docs/cognition/` has | `spec/canonical/core/cognition/` has |
|---|---|---|
| TASK_CLASSIFICATION | Full classification tree, 4 rules, re-classification trigger | PTD rules, token budgets per PATH, decomposition depth |
| CONTEXT_BUDGET | 30/70 rule, compression techniques (skeletonizing, pruning, masking), budget breach protocol | Scenario targets (KB), load strategy, anti-patterns |
| path-routing | Per-PATH load strategy (what files to load), Portuguese heuristics | PATH descriptions with token budgets, PATH declaration block |

**Treatment:** Merge unique content from `docs/cognition/` into `spec/canonical/core/cognition/`
following the IA First schema. Then retire `docs/cognition/` — replace each file with a
one-line pointer to the canonical location.

Merge rules:
- `spec/canonical/` receives the unique content sections from `cognition/`
- Prose and Portuguese explanations are distilled into IA First format (lists, short rules)
- No section in the merged file exceeds 5 items
- `docs/cognition/` files become pointers: `> See: spec/canonical/core/cognition/<file>`

Files affected:
- `docs/spec/canonical/core/cognition/decision-models/TASK_CLASSIFICATION.md` — absorbs classification tree + rules
- `docs/spec/canonical/core/cognition/context-loading/context-budget.md` — absorbs compression techniques + budget breach protocol
- `docs/spec/canonical/core/cognition/context-loading/path-routing.md` — absorbs per-PATH load strategy
- `docs/cognition/decision-models/TASK_CLASSIFICATION.md` → pointer
- `docs/cognition/context-loading/CONTEXT_BUDGET.md` → pointer
- `docs/cognition/context-loading/path-routing.md` → pointer
- All other `docs/cognition/` files: audit individually — pointer if duplicate, keep if unique

---

### Situation 3 — Same Name, Different Layer (differentiate, keep both)

`docs/spec/canonical/core/generated/AGENT_ENTRYPOINT.md` (IA First execution kernel —
immutable governance) and `docs/runtime/protocols/AGENT_ENTRYPOINT.md` (operational
workspace bootstrap instructions) serve completely different purposes.

Same applies to their AGENT_RUNTIME_PROTOCOL counterparts.

**Treatment:** Keep both. Add a `> Layer:` declaration at the top of each file to make
the distinction explicit and machine-readable:

```markdown
> Layer: spec/canonical — immutable governance definition
```
or
```markdown
> Layer: runtime — operational agent instructions
```

Files updated (header addition only):
- `docs/spec/canonical/core/generated/AGENT_ENTRYPOINT.md`
- `docs/spec/canonical/core/generated/AGENT_RUNTIME_PROTOCOL.md`
- `docs/runtime/protocols/AGENT_ENTRYPOINT.md`
- `docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md`

---

### Situation 4 — INDEX.md vs index.md Case Inconsistency

Mixed casing across 17 index files. `spec/canonical/core/` subdirs use `index.md`
(lowercase); top-level dirs use `INDEX.md` (uppercase).

**Treatment:** Standardize to uppercase `INDEX.md` across all directories. Lowercase
`index.md` files are renamed; all internal links referencing them are updated.

Scope: 10 `index.md` files in `spec/canonical/core/` subdirs.

---

## Execution Sequence

1. Delete stubs (Situation 1) — no content risk
2. Standardize INDEX casing (Situation 4) — mechanical, no content change
3. Merge cognition content into canonical (Situation 2) — requires review per file
4. Add Layer declarations (Situation 3) — header addition only

## Files Affected Summary

| File | Action |
|---|---|
| `docs/runtime/AGENT_ENTRYPOINT.md` | Delete (stub) |
| `docs/runtime/AGENT_RUNTIME_PROTOCOL.md` | Delete (stub) |
| `docs/spec/canonical/core/generated/AGENT_ENTRYPOINT.md` | Add Layer header |
| `docs/spec/canonical/core/generated/AGENT_RUNTIME_PROTOCOL.md` | Add Layer header |
| `docs/runtime/protocols/AGENT_ENTRYPOINT.md` | Add Layer header |
| `docs/runtime/protocols/AGENT_RUNTIME_PROTOCOL.md` | Add Layer header |
| `docs/spec/canonical/core/cognition/**` (3 files) | Merge content from cognition/ |
| `docs/cognition/**` (3+ files) | Convert to pointers |
| 10× `index.md` in `spec/canonical/core/` | Rename to `INDEX.md` |

## Acceptance Criteria

1. Zero files with identical content in different locations.
2. Every `cognition/` file either points to canonical or contains content not present in canonical.
3. All `AGENT_ENTRYPOINT` and `AGENT_RUNTIME_PROTOCOL` files have a `> Layer:` declaration.
4. All index files use `INDEX.md` (uppercase).
5. No broken links introduced by deletions or renames (verified by `check_links.py --mode ci`).
