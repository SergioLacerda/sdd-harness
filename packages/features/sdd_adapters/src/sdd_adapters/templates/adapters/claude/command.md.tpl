---
name: {{ skill.name if skill.name is defined else skill.id }}
description: {{ skill.description }}
---

{% set cmd_name = skill.name if skill.name is defined else skill.id %}
{% set routes_to = skill.routes_to if skill.routes_to is defined else None %}
{% set is_cli = routes_to and routes_to.type == "cli" %}
# /{{ cmd_name }}

{% if is_cli %}
Execute SDD CLI command `{{ routes_to.command }}`.

## Execution

Run: `{{ routes_to.command }} "$ARGUMENTS"`

Pass user arguments directly to the CLI command. Do not interpret or modify the arguments.

## When to use

{{ skill.description }}

{% else %}
Load and execute SDD skill `{{ cmd_name }}`.

## Required steps

1. Read `.sdd/agent-instructions.md`
2. Read `.sdd/skills/registry.json`
3. Confirm skill is registered as `{{ cmd_name }}`
4. Read `.sdd/skills/{{ cmd_name }}/skill.yaml`
{% if skill.skill_md is defined %}5. Read `.sdd/skills/{{ cmd_name }}/SKILL.md` for full protocol
{% endif %}5. Follow the skill protocol

## Allowed CLI

{% for cmd in skill.allowed_tools %}
- `{{ cmd }}`
{% endfor %}

## Risk

`{{ skill.risk_score }}` — {{ skill.description }}
{% if skill.skill_md is defined %}

## Protocol

Read `.sdd/skills/{{ cmd_name }}/SKILL.md` for the full execution protocol, output format, and non-compliance rules.
{% endif %}
{% endif %}

## Non-compliance

Do not invent SDD commands.
Do not bypass the skill registry.
Declare degraded mode if `.sdd/skills/registry.json` is unavailable.
