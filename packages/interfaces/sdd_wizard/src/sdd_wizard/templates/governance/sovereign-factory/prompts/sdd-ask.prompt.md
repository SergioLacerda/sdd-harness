---
description: Query SDD governance context
mode: agent
---

Query the SDD governance context with the user's question.

Execute in the terminal:
```bash
sdd runtime status
sdd governance validate
sdd ask --full "$QUERY"
```

Replace `$QUERY` with the user's question.

HARD contract for this command:
- Run preflight in order (`sdd runtime status` then `sdd governance validate`).
- If preflight fails, do not continue; return governance-blocked status.
- Only continue to `sdd ask --full` when preflight is healthy.

Response contract:
- Show `fingerprint`, `context_source`, and `mandates_loaded` from runtime output.
- Treat `.sdd` runtime artifacts as source of truth for these fields.

SDD GOVERNANCE CHECK
- Always end responses with this compact footer:
  `SDD GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}`

Audit JSON policy:
- `.sdd/compiled/audit/*.json` is human/audit oriented.
- Agents should prefer `.sdd/source/*` for human-readable governance context and
  runtime checks (`sdd runtime status`, `sdd ask --full`) for operational state.
