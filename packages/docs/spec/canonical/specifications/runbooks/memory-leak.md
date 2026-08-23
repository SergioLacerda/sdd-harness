# Memory Leak Detected

## Symptoms

- RSS/heap usage grows continuously without returning to baseline.
- OOM kills or container restarts occur.
- GC pressure and latency increase over time.

## Diagnosis

1. Compare memory profile before/after latest deploy.
2. Inspect object growth hotspots via profiler.
3. Check long-lived caches/queues for unbounded growth.
4. Correlate leak onset with feature flags or traffic pattern changes.

## Resolution Steps

1. Apply emergency cap/eviction to unbounded structures.
2. Disable offending feature flag if identified.
3. Roll back release if leak introduced recently.
4. Verify stabilization by observing flat memory trend windows.

## Rollback

1. Roll back to last known-good build.
2. Restore prior memory-related configuration thresholds.

## Post-Incident

- Add leak regression test or benchmark scenario.
- Document root cause and preventive guardrail.
- Track permanent fix in roadmap.
