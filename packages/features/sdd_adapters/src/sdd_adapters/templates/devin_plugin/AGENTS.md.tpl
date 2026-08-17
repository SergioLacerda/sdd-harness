# SDD Governance Projection for Devin

Profile: **Soft/Standalone**
Provider: `devin`
Plugin version: `{{ plugin_version }}`
Policy digest (embedded snapshot): `sha256:{{ policy_digest }}`
Source revision: `{{ source_revision }}`
Built at: `{{ built_at }}`

## Assurance disclosure

This plugin ships an embedded snapshot of SDD Harness governance skills. It has **not** verified a live SDD Harness connection for this session.

- `policy_source: embedded_snapshot`
- `assurance: reduced`
- `external_dependencies: none`

Soft/Standalone assurance is never equivalent to a connected Hard/Connected SDD Harness session. Do not represent this plugin's governance as equivalent to a live-verified SDD policy.

## Precedence order

1. Provider or organization safety controls (Devin's own permissions/config).
2. Connected SDD hard policy (not active in this profile).
3. Project canonical policy (this project's own `.sdd/`, if present).
4. Embedded SDD snapshot (this plugin's `skills/`).
5. Provider local rules (`.devin/config.json`, project `AGENTS.md`, `rules/`).
6. User task instructions.

## Skill discovery

Skills embedded in this plugin are listed under `skills/`. Each skill file documents its own allowed CLI commands and risk score. Do not invent commands beyond what a skill file declares.

## SDD Harness Summary (embedded snapshot)

Governance fingerprint: `{{ governance_fingerprint }}`
Workspace version: `{{ workspace_version }}`
Mandate count: `{{ mandate_count }}`
Governance summary digest: `sha256:{{ governance_summary_digest }}`

This is an index, not policy text — mandate IDs and titles only. Full detail (where available in the source) is in `rules/sdd-harness-summary.md`. Neither is canonical; see `metadata/provenance.json` for the source revision this was compiled from.

Mandates:
{% for m in mandates %}
- `{{ m.id }}` — {{ m.title }}
{% endfor %}

Guideline categories:
{% for g in guideline_categories %}
- {{ g }}
{% endfor %}

## Canonical source

This plugin is a generated projection. It is **not** the canonical governance source. Canonical SDD Harness policy lives in the `.sdd/` directory of the SDD Harness project this plugin was compiled from — see `metadata/provenance.json` for the exact source revision.
