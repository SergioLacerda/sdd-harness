# RUNBOOKS CANONICAL INDEX

## Objective

Centralize SRE-style production-incident runbooks: symptoms, diagnosis,
resolution, rollback, and post-incident steps for known operational failure
modes of the running system.

This is distinct from [`docs/runbooks/`](../../../../runbooks/README.md), which
covers process/CI/release incidents (build failures, docs publishing, dependency
vulnerability remediation) rather than production-service failures.

## Runbooks

- [db-slow-queries.md](./db-slow-queries.md)
- [llm-rate-limited.md](./llm-rate-limited.md)
- [memory-leak.md](./memory-leak.md)
- [vector-search-down.md](./vector-search-down.md)
- [elevated-error-rate.md](./elevated-error-rate.md)
- [deployment-rollback-failure.md](./deployment-rollback-failure.md)
- [disk-storage-exhaustion.md](./disk-storage-exhaustion.md)

## Structure

Every runbook follows the same five sections: Symptoms, Diagnosis, Resolution
Steps, Rollback, Post-Incident.

## Rule

Use these runbooks under PATH E (active production incident) per
[`context-loading/path-routing.md`](../../core/cognition/context-loading/path-routing.md).
