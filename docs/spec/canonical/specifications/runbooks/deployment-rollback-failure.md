# Deployment Rollback Failure

## Symptoms

- A rollback is triggered but the previous version fails to become healthy.
- Traffic remains on the bad release, or the service enters a crash-loop on both
  versions.
- Deployment tooling reports the rollback as stuck or failed.

## Diagnosis

1. Confirm which version is actually receiving traffic vs. which version the
   deployment tool believes is active.
2. Check whether the rollback target version is compatible with current
   infrastructure state (schema migrations, config, feature flags) — a rollback
   after a forward-only migration is a common cause.
3. Inspect health-check/readiness-probe failures on the rollback target.
4. Check for resource contention (insufficient capacity to run both versions
   during the transition).

## Resolution Steps

1. If a forward-only migration is the blocker, apply a compensating fix-forward
   instead of a rollback — do not attempt a rollback that reintroduces a schema
   mismatch.
2. If the rollback target is otherwise healthy, manually shift traffic once
   health checks pass, bypassing an automation step that is stuck.
3. If neither is safe, scale up capacity to run a known-good version alongside
   the failing one while investigating.
4. Validate recovery by confirming traffic is on a healthy version and error/
   latency metrics return to baseline.

## Rollback

1. This runbook's own subject is rollback failure — if the fix-forward path is
   also unsafe, escalate to manual traffic draining and a maintenance window
   rather than repeating automated rollback attempts.

## Post-Incident

- Record whether the failure was caused by a non-reversible migration; if so,
  track a follow-up to make future migrations backward-compatible.
- Add a pre-rollback compatibility check to deployment tooling if missing.
- Document the exact failure mode for the next on-call.
