---
description: {{ command.id }} command adapter
---

Source: `.sdd/commands/{{ command.id }}/command.yaml`

Steps:
1. Read `.sdd/agent-instructions.md`
2. Run `sdd runtime status`
3. Run `sdd governance validate`
4. Execute:
{% if command.routes_to.type == "cli" %}
   `{{ command.routes_to.command }}`
{% elif command.routes_to.type == "skill" %}
   `sdd skills run {{ command.routes_to.id }}`
{% else %}
   `echo "Invalid command routes_to configuration"`
{% endif %}
5. Return `policy_result` and `next_actions`

{% include "_governance_contract.md" %}
