# Failure Ledger

Operational log of failures, root causes, and preventive actions.
One entry per confirmed incident. Append-only — do not edit past entries.

---

## How to Use

1. Open a new case when a regression or production failure is confirmed.
2. Fill all fields before marking the case Closed.
3. "Confirmed cause" requires evidence (test, log line, or code reference).
4. "Preventive action" must be a specific, testable change — not a vague intention.

---

## Template

```
## Case NNN — YYYY-MM-DD — <short title>

- **Symptom**: Observable failure description
- **Failing test**: `test_file.py::test_name` or CI step
- **Affected scope**: package(s) / module(s)
- **Suspected cause**: Initial hypothesis
- **Confirmed cause**: Evidence-backed root cause (file:line)
- **Patch applied**: Files changed + commit reference
- **Validation executed**: Test suite(s) run + result
- **Regression introduced?**: Yes / No — evidence
- **Preventive action**: Specific change that prevents recurrence
- **Status**: Open | Closed
```

---

## Active Cases

_(none)_

---

## Closed Cases

_(none yet — first entry will be added here)_
