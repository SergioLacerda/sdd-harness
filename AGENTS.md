# Agent Bootstrap Paths
<!-- Governance fingerprint: a3d875a1 -->
<!-- Active mandates: 1 (M001) -->
<!-- Generated: 2026-06-14T12:05:01.585942Z -->
<!-- Drift check: fingerprint must match .sdd/metadata.json → governance_fingerprint -->

Objective: standardize where each agent must load local instructions, commands, and skills in this project.

## Mandatory Rules

1. Always prioritize local project files/folders before global sources.
2. On startup, each agent must read its dedicated path(s) listed below.
3. If `SKILL.md`, `*.md`, `commands/`, `prompts/`, or equivalent files exist, load them as operational context.
4. You are under governance: always resolve authoritative rules from `.sdd`.
   Initial reference: `.sdd/agent-instructions.md`.

## Governance Authority (`.sdd`)

1. Governance is mandatory and authoritative from `.sdd`.
2. Initial reference: `.sdd/agent-instructions.md`.
3. If any local/global convenience file conflicts with `.sdd`, follow `.sdd`.

## Commands And Skills (Source Of Truth)

1. Commands source of truth: `.sdd/commands`.
2. Skills source of truth: `.sdd/skills`.
3. On startup, agents must load:
   - `.sdd/commands/registry.json`
   - `.sdd/skills/registry.json`
4. For each active command/skill in the registries, agents must read canonical files before use:
   - Commands: `.sdd/commands/<command-id>/command.yaml`
   - Skills: `.sdd/skills/<skill-name>/skill.yaml`
5. If registry or canonical file is missing/inconsistent, register bootstrap drift and continue in safe fallback mode without inventing missing rules.

## Agent-Specific Paths

- Codex: `./.codex/`
- Claude: `./CLAUDE.md`, `./.claude/commands/`
- Gemini: `./.gemini/`
- GitHub Copilot: `./.github/copilot-instructions.md`, `./.github/prompts/`
- Cursor: `./.cursor/rules/`
- VS Code Prompts: `./.github/prompts/`
## Minimal Fallback

If a dedicated path does not exist:

1. Register that local bootstrap is missing.
2. Continue with default agent behavior, without inventing local context.
