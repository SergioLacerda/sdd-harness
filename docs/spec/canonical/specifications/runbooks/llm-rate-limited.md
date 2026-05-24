# LLM API Rate Limited

## Symptoms
- Upstream returns HTTP 429 or quota errors.
- Request retries increase and user response time degrades.
- Throughput drops while queue depth increases.

## Diagnosis
1. Check provider status/quota dashboard.
2. Confirm current request rate against configured limits.
3. Inspect retry/backoff telemetry.
4. Verify if recent traffic spike or batch job triggered contention.

## Resolution Steps
1. Enable stricter client-side backoff and jitter.
2. Reduce non-critical traffic (defer batch/background work).
3. Switch to configured fallback model/provider if available.
4. Validate recovery by monitoring 429 rate and p95 latency.

## Rollback
1. Revert temporary throttling changes after stabilization.
2. Restore normal routing policy once provider normalizes.

## Post-Incident
- Record exact quota/limit threshold hit.
- Add capacity planning action item.
- Review fallback coverage in contract tests.
