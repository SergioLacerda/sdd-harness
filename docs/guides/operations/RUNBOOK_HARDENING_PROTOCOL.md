# Runbook Hardening Protocol

Approved: yes
Decision-Owner: Sergio Lacerda
Decision-Date: 2026-05-24
Review-Cadence: monthly

## Drill Cadence

- Execute at least one operational drill per month.
- Alternate scenario families:
  - release failure / rollback
  - telemetry/metrics outage
  - governance/runtime state drift

## Drill Record Template

Each drill entry must capture:

- `drill_id`
- `scenario`
- `started_at`
- `resolved_at`
- `mttr_minutes`
- `owner`
- `outcome` (pass/fail)
- `follow_up_actions`

## SLO Verification

Minimum readiness checks:

- MTTR target: <= 60 minutes for known scenarios
- Runbook coverage: top recurring incidents documented
- Verification evidence attached in `docs/incidents/FAILURE_LEDGER.md`

## Postmortem Feedback Loop

After each failed or degraded drill:

1. Append incident/drill record to `docs/incidents/FAILURE_LEDGER.md`.
2. Update affected playbook section in `docs/incidents/PLAYBOOKS.md`.
3. Register remediation owner and due date.
4. Re-run drill scenario after remediation and compare MTTR delta.
