# Vector Search Down

## Symptoms

- Search endpoints time out or return empty results unexpectedly.
- Error rate spikes on vector retrieval calls.
- Latency increases above SLO for retrieval operations.

## Diagnosis

1. Check vector index service health and recent restarts.
2. Inspect application logs for adapter/port errors.
3. Confirm index files/storage availability.
4. Validate recent deployments and config changes.

## Resolution Steps

1. Restart affected vector index process or pod.
2. Roll back latest deployment if regression is confirmed.
3. Rebuild or reload index if corruption is detected.
4. Re-run smoke query set and verify latency/error recovery.

## Rollback

1. Revert to last known-good release.
2. Restore previous index snapshot.

## Post-Incident

- Open follow-up issue for root cause.
- Update this runbook with new failure mode, if discovered.
- Add regression alert if missing.
