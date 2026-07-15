---
description: {{ command.id }} command adapter
mode: agent
---

## Source

`.sdd/commands/{{ command.id }}/command.yaml`

## Required behavior

1. Run preflight: `sdd runtime status`
2. Validate governance: `sdd governance validate`
3. Execute:
{% if command.routes_to.type == "cli" %}
   `{{ command.routes_to.command }}`
{% elif command.routes_to.type == "skill" %}
   `sdd skills run {{ command.routes_to.id }}`
{% else %}
   `echo "Invalid command routes_to configuration"`
{% endif %}
4. Return `policy_result` and `next_actions`
{% if command.routes_to.note %}
## Adapter note

{{ command.routes_to.note }}
{% endif %}

## SDD GOVERNANCE

`SDD GOVERNANCE: drift=${status} | governance=${status} | profile={{ command.id }}`
