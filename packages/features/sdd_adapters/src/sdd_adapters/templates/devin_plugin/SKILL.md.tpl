---
name: {{ skill.name }}
description: {{ skill.description }}
allowed-tools:
{% for cmd in skill.allowed_tools | default([], true) %}
  - {{ cmd }}
{% endfor %}
triggers:
{% for t in skill.triggers | default([], true) %}
  - {{ t }}
{% endfor %}
---

# {{ skill.name }}

Source of truth: `.sdd/skills/{{ skill.name }}/skill.yaml` in the SDD Harness repository this plugin was generated from.

## When to use

{% for t in skill.when_to_use | default([], true) %}
- {{ t }}
{% endfor %}

## Profile disclosure

This plugin operates in **Soft/Standalone** profile: `policy_source=embedded_snapshot`, `assurance=reduced`, `external_dependencies=none`. The embedded snapshot may drift from the canonical SDD Harness source between plugin releases. Do not treat this file as authoritative if a connected SDD Harness promotes this session to Hard/Connected profile.

## Required steps

1. Confirm this skill (`{{ skill.name }}`) is listed under `skills/` of this plugin.
2. Follow the steps below using only the allowed CLI commands.
3. Report `policy_result` and any governance fields verbatim.

## Allowed CLI

{% for cmd in skill.allowed_tools | default([], true) %}
- `{{ cmd }}`
{% endfor %}

## Risk

`{{ skill.risk_score | default("controlled", true) }}`
