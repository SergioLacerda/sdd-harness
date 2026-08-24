# TEST GOVERNANCE

## Objective

Use tests as convergence constraints, not as brute-force validation.

## MUST

- Run local/unit checks first.
- Expand test scope incrementally by impact evidence.
- Keep failing-test analysis attached to each retry.

## MUST NOT

- Run full suite by default.
- Retry failing suites blindly.
- Ignore flaky signal without containment action.

## INVALID

- Declaring completion without impacted-scope passing tests.
- Skipping mandatory quality gates for code changes.

## Escalation/Recovery

- On repeated failures: perform drift analysis and scope reassessment.
- If still unstable: quarantine flaky path and escalate.
