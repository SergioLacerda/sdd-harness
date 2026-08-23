# ADR-009 Companion — CI Fail-Closed Enforcement Matrix

**Status:** Accepted
**Date:** 2026-08-07
**Companion to:** `ADR-020-progressive-enforcement-ladder.md`

---

## Purpose

Maps the specific CI controls investigated in
`.analysis/refined/20260807-ci-fail-closed-matrix-fix/` onto ADR-009's existing
`warn` / `block` / `strict` phases (see that ADR for the full phase-semantics
table, promotion criteria, and rollback triggers — not restated here). Every
`warn`-phase row below carries an explicit owner and expiration, per ADR-009's own
requirement that promotion be evidence-based, not left indefinitely advisory.

## Matrix

| Control | Location | Phase | Owner | Expiration | Rationale |
|---|---|---|---|---|---|
| Docs links — modified-in-PR | `docs.yml` "Check internal docs links (PR diff-aware blocking)" | block | docs maintainer | — | Diff-aware; only fails on links touched by the current PR, so authors always have a local fix path |
| Docs links — full-repo/legacy | `docs.yml` "Check internal docs links (advisory baseline)" | warn | docs maintainer | 2026-11-07 | Full-repo baseline includes pre-existing legacy links not caused by the current change; promote to `block` once a legacy-link remediation pass clears the baseline |
| Markdown style | `docs.yml` "Markdown style advisory (non-blocking)" | warn | docs maintainer | 2026-11-07 | Style-only, non-semantic; promote once `markdownlint-cli2` baseline is clean repo-wide |
| Governance-audit signature | `reusable-governance.yml` "Security Audit (informational)" | warn | governance owner | 2026-09-07 | Blocked on ephemeral-key wiring (see `implementation_handoff` in `tasks.md`) — production signing key is not available in CI; ephemeral per-job keygen already proven in `release.yml`'s signing smoke test |
| Trusted-keyring precedence | `reusable-security.yml` (`environment_gates.py trusted-keyring-precedence-check`) | warn | governance owner | 2026-09-07 | Same root cause as governance-audit signature — gate only reaches `enforce` semantics when `SDD_SIGNATURE_MODE=strict` is set, which requires the same ephemeral-key wiring |
| Signature-mode policy | `reusable-security.yml` (`environment_gates.py signature-mode-policy-check`) | warn | governance owner | 2026-09-07 | Same root cause as above |

## Explicitly Excluded

- **Docker Hub login** (`reusable-security.yml` "Log in to Docker Hub",
  `continue-on-error: true`) — not a security-enforcement control. It tolerates
  missing registry credentials (e.g. fork PRs without secrets) so the subsequent
  `docker build` step, which does not require registry auth, can still run. Listed
  here only so a future audit doesn't re-flag it as an enforcement gap.

## Promotion Path

The three `warn`-phase rows sharing the signing root cause (governance-audit
signature, trusted-keyring precedence, signature-mode policy) promote together,
gated on the ephemeral-key wiring landing in `reusable-governance.yml` (tracked as
`implementation_handoff` in the originating Strategist mission,
`20260807-ci-fail-closed-matrix-fix`). Once that lands and is stable per ADR-009's
promotion criteria (failure rate, false-positive rate, MTTR, audit-completeness —
see ADR-009 § Promotion criteria), all three move to `block`.

## Links

- `docs/adr/ADR-020-progressive-enforcement-ladder.md` (parent ADR — phase semantics, promotion/rollback criteria, telemetry requirement)
- `.github/workflows/release.yml` (existing ephemeral-key proof of concept: `governance keygen` → `sign` → `audit`)
- `.analysis/refined/20260807-ci-fail-closed-matrix-fix/` (originating Strategist mission)
