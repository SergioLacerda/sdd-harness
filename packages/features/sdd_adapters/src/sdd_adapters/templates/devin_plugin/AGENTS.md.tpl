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

## Canonical source

This plugin is a generated projection. It is **not** the canonical governance source. Canonical SDD Harness policy lives in the `.sdd/` directory of the SDD Harness project this plugin was compiled from — see `metadata/provenance.json` for the exact source revision.
