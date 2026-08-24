# Database Slow Queries

## Symptoms

- DB query latency crosses SLO thresholds.
- API endpoints dependent on DB slow down or timeout.
- Connection pool saturation or queue growth appears.

## Diagnosis

1. Identify top slow queries from DB telemetry.
2. Check execution plans for regressions/full scans.
3. Verify index presence and recent schema changes.
4. Inspect lock contention and concurrent write pressure.

## Resolution Steps

1. Apply safe query/index optimization for top offenders.
2. Reduce expensive background jobs temporarily.
3. Increase timeout/retry only as short-term mitigation.
4. Validate p95/p99 recovery after changes.

## Rollback

1. Revert recent migration/query change if regression confirmed.
2. Restore previous query path or feature flag state.

## Post-Incident

- Add alert for early slow-query threshold.
- Capture optimized query plan in docs.
- Schedule permanent schema/query remediation.
