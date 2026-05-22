# Failure Ledger

Operational log of failures, root causes, and preventive actions.
One entry per confirmed incident. Append-only — do not edit past entries.

---

## How to Use

1. Open a new case when a regression or production failure is confirmed.
2. Fill all fields before marking the case Closed.
3. "Causa confirmada" requires evidence (test, log line, or code reference).
4. "Ação preventiva" must be a specific, testable change — not a vague intention.

---

## Template

```
## Case NNN — YYYY-MM-DD — <short title>

- **Sintoma**: Observable failure description
- **Teste que falhou**: `test_file.py::test_name` or CI step
- **Escopo afetado**: package(s) / module(s)
- **Causa suspeita**: Initial hypothesis
- **Causa confirmada**: Evidence-backed root cause (file:line)
- **Patch aplicado**: Files changed + commit reference
- **Validação executada**: Test suite(s) run + result
- **Regressão criada?**: Yes / No — evidence
- **Ação preventiva**: Specific change that prevents recurrence
- **Status**: Open | Closed
```

---

## Active Cases

_(none)_

---

## Closed Cases

_(none yet — first entry will be added here)_
