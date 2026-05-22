---
name: {{ skill.name }}
description: {{ skill.description }}
---

## Source

- `.sdd/skills/{{ skill.name }}/skill.yaml`
{% if skill.skill_md is defined %}- `.sdd/skills/{{ skill.name }}/SKILL.md` (full protocol)
{% endif %}

## Invocation

Use when:
{% for t in skill.when_to_use %}
- {{ t }}
{% endfor %}

## Required steps

1. Load `.sdd/agent-instructions.md`
2. Load `.sdd/skills/registry.json`
3. Confirm skill `{{ skill.name }}` is registered
4. Follow the SDD skill protocol
5. Use only allowed CLI

## Allowed CLI

{% for cmd in skill.allowed_tools %}
- `{{ cmd }}`
{% endfor %}

## Risk

`{{ skill.risk_score }}`
