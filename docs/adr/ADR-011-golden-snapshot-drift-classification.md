# ADR-011 — Golden Snapshot Drift Classification

**Status:** Accepted
**Date:** 2026-05-21
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

Contract and golden snapshot tests were updated ad-hoc: a failing test triggered a
snapshot refresh with no record of why the output changed or whether the change was
intentional. This made it impossible to distinguish accidental regressions from
deliberate output evolution, and snapshot updates in PRs had no review protocol.

---

## Decision

**All golden snapshot drift is classified before acceptance. Classification determines
the required evidence and review path.**

### Drift types

| Type | Description | Review path |
|---|---|---|
| **A** | Volatile-only changes (timestamps, `generated_at`, UUIDs, process ids) | Automatic acceptance; no human review required |
| **B** | Backward-compatible structural change (new field added, optional field removed) | Diff artifact required; reviewer checklist sign-off |
| **C** | Breaking structural or semantic change (field renamed/removed, contract meaning changed) | Diff artifact + rationale + link to governing plan/spec; requires proposal update before snapshot acceptance |

### Evidence requirements (B and C)

1. **Diff artifact:** the full before/after snapshot diff is attached to the PR or commit.
2. **Rationale:** a written explanation of why the output changed.
3. **Governing link:** for Type C, a link to the spec, design, or plan that authorized
   the change.

### Policy controls

- Golden snapshot updates require an explicit command path (e.g., `make update-snapshots`);
  they cannot be committed silently by a test run.
- Type C changes block merge until the governing spec/plan is updated first — the snapshot
  reflects the spec, not the reverse.
- Contract failures (invariant violations, not just snapshot drift) block protected-branch
  merges unconditionally.

### Lifecycle

```
drift detected
  → classify (A / B / C)
  → attach evidence (B: diff; C: diff + rationale + link)
  → reviewer checklist sign-off (B, C)
  → snapshot update committed
  → merge unblocked
```

---

## Rationale

- **Ad-hoc refresh rejected:** no audit trail; regressions accepted silently alongside
  intentional changes.
- **Blanket block-on-any-diff rejected:** volatile fields (timestamps) make tests
  non-deterministic with no governance value.
- **Typed classification accepted:** separates noise (Type A) from signal (B, C) and
  scales the review burden to the actual risk of the change.

---

## Consequences

- CI must detect drift type before reporting a failure; a generic "snapshot mismatch"
  error without classification is insufficient.
- Type A fields must be explicitly listed in a configuration file so the classifier
  knows which fields to treat as volatile.
- The presence of a Type C change without a governing spec/plan link blocks merge
  regardless of reviewer approval.

---

## Links

- Related: ADR-001 (Runtime Authority Boundary)
