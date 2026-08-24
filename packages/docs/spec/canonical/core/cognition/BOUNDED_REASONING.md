# BOUNDED REASONING

## Objective

Treat reasoning depth as a governed resource.

## MUST

- Use bounded reflection loops.
- Stop retries after threshold when no new evidence exists.
- Prefer convergence over exploration breadth.

## MUST NOT

- Enter recursive reasoning loops.
- Expand context indefinitely.
- Re-open settled decisions without new signal.

## INVALID

- Any loop with repeated rationale and unchanged evidence.
- Any context expansion that exceeds declared path budget without reclassification.

## Escalation/Recovery

- Reduce scope and reassess task classification.
- Trigger human escalation when bounded attempts are exhausted.
