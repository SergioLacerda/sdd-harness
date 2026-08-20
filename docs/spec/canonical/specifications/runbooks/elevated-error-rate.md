# Elevated Error Rate

## Symptoms

- 5xx/error rate crosses SLO threshold on one or more endpoints.
- Alerting fires on error-budget burn rate.
- Downstream consumers report failed or degraded requests.

## Diagnosis

1. Identify which endpoints/services are contributing most to the error spike.
2. Correlate onset with the most recent deploy, config change, or feature flag flip.
3. Inspect error logs/traces for a dominant error class (timeout, panic, upstream
   5xx, validation failure).
4. Check dependency health (database, cache, downstream APIs) for a shared root
   cause.

## Resolution Steps

1. Roll back the most recent deploy if the onset correlates with it.
2. Disable the offending feature flag if identified.
3. Apply a targeted fix (timeout tuning, circuit breaker, input validation) for the
   dominant error class.
4. Validate recovery by watching error rate and p95/p99 latency return to baseline.

## Rollback

1. Revert to the last known-good release.
2. Restore prior configuration/feature-flag state.

## Post-Incident

- Add or tighten alerting for the specific error signature that caused the spike.
- Add a regression test covering the failure mode.
- Document root cause and the guardrail added to prevent recurrence.
