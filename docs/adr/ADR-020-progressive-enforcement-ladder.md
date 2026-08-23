# ADR-020 — Progressive Enforcement Ladder (WARN → BLOCK → STRICT)

**Status:** Accepted
**Date:** 2026-05-21
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

Governance enforcement for mandates (M001–M012) previously had two effective states:
ignored or hard-blocked. Enabling enforcement for a new rule required immediate CI
breakage tolerance, which discouraged teams from enabling rules until violations had
already accumulated.

---

## Decision

**Governance enforcement follows a three-phase ladder. Rules advance through phases
based on measured stability, not by calendar.**

```
WARN  →  BLOCK  →  STRICT
 |         |          |
advisory  merge      hard runtime
signal    prevention enforcement
```

### Phase semantics

| phase | behaviour | gate context | owner |
|---|---|---|---|
| warn | Emit advisory signal; do not fail build on missing evidence | `make check` / local validation | feature author |
| block | Fail on missing evidence; require reviewer approval for class B/C | CI `artifact-gate` (`reusable-test.yml`) | maintainer + governance reviewer |
| strict | Fail on any missing approval (A/B/C) + class C artifact validity | release/hard gate contexts | governance owner |

### Promotion criteria (WARN → BLOCK, BLOCK → STRICT)

A rule may advance when all of the following thresholds are met:

1. Failure rate below configured stability threshold for the observation window.
2. False-positive rate below configured threshold.
3. Mean time to remediation within acceptable bound.
4. Audit completeness: every enforcement decision has a telemetry record.

### Rollback triggers

A rule reverts one phase when:

- Unexpected false-block spike is detected.
- Tooling reliability regression is confirmed.
- Observability for enforcement decisions is incomplete (cannot postmortem a block).

### Telemetry requirement

Every enforcement decision must emit a `RuntimeEvent` with enough metadata to support
postmortem and policy tuning. A block without a telemetry record is a ladder violation.

---

## Rationale

- **Binary enforce/skip rejected:** activating a rule is all-or-nothing, which creates
  an incentive to delay activation indefinitely.
- **Calendar-based promotion rejected:** time elapsed is a poor proxy for rule stability;
  promotion must be evidence-based.
- **Three-phase ladder accepted:** teams can observe rule behaviour under WARN before
  accepting CI impact, and rollback is a defined operation rather than a special case.

---

## Consequences

- New governance rules start at WARN. No rule may skip to BLOCK or STRICT on introduction.
- The promotion/rollback decision requires telemetry evidence — subjective judgement alone
  is insufficient.
- Runtime code that enforces at STRICT phase must emit a `RuntimeEvent` before aborting;
  silent hard-fail is a policy violation.

---

## Links

- Policy matrix: `docs/adr/ADR-020-progressive-enforcement-ladder.md` (this file)
- Threshold signoff: `docs/adr/ADR-021-threshold-signoff.md`
- Related: M010 (Governance Hardening), ADR-001 (Runtime Authority Boundary)
