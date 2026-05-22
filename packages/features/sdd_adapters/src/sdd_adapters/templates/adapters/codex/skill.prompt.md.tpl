---
description: {{ skill.description }}. Use when: {% for t in skill.when_to_use %}{{ t }}{% if not loop.last %}, {% endif %}{% endfor %}.
mode: agent
---

## Source

`.sdd/skills/{{ skill.name }}/skill.yaml`{% if skill.skill_md is defined %} · `.sdd/skills/{{ skill.name }}/SKILL.md`{% endif %}

## Required behavior

1. Run preflight: `sdd runtime status`
2. Validate governance: `sdd governance validate`
{% if skill.category in ["analysis", "governance"] %}
3. For large inputs: `sdd organize "$QUERY"` before proceeding
{% endif %}
4. Execute: `{{ skill.cli_fallback[0] }}`
5. Return `policy_result` and `next_actions`

## Allowed CLI

{% for cmd in skill.allowed_tools %}
- `{{ cmd }}`
{% endfor %}
{% if skill.skill_md is defined %}

## Non-compliance

- Do not invent SDD commands not listed above
- Do not skip preflight or governance validate
- Declare degraded mode if `.sdd/skills/registry.json` is unavailable
- See `.sdd/skills/{{ skill.name }}/SKILL.md` for complete non-compliance rules
{% endif %}

## SDD GOVERNANCE

`SDD GOVERNANCE: drift=${status} | governance=${status} | profile={{ skill.name }}`

Agents must prefer `.sdd/source/*` for governance context over compiled artifacts.
