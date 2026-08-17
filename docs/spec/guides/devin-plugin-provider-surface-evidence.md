# Devin Plugin Provider Surface — Verification Evidence

**Verified:** 2026-08-17
**Verified by:** live web search + fetch against `docs.devin.ai` (no pinned local fixture existed prior to this note).

## Sources

- https://docs.devin.ai/cli/extensibility/plugins/overview — plugin manifest schema, directory layout, install sources.
- https://docs.devin.ai/cli/extensibility/configuration — `.devin/config.json`, `.devin/config.local.json`, permissions syntax.
- https://docs.devin.ai/cli/extensibility/rules — `AGENTS.md` / rules discovery and precedence.
- https://docs.devin.ai/cli/extensibility/hooks/overview — `hooks.v1.json` / `hooks.json` schema, event names, stdin/stdout contract.
- https://docs.devin.ai/cli/extensibility/skills/creating-skills — `SKILL.md` frontmatter.

## Confirmed plugin bundle shape

```text
my-plugin/
├── .devin-plugin/
│   └── plugin.json     # primary manifest (fallback: .claude-plugin/plugin.json, root plugin.json)
├── AGENTS.md            # always-on rule
├── rules/               # optional, triggered rules
├── agents/              # optional, custom subagents
├── hooks.json           # optional, lifecycle hooks
├── .mcp.json            # optional, MCP servers
└── skills/
    └── {name}/SKILL.md
```

## Confirmed `plugin.json` fields

`name` (required), `version`, `description`, `author{name,email}`, `homepage`, `repository`, `license`, `keywords`, `skills` (path list, default `skills/`), `mcpServers`, `requiredPlugins`, `optionalPlugins`, `forbiddenPlugins`.

## Confirmed `hooks.json` schema

Top-level keys are event names directly (no wrapper key). Confirmed events: `PreToolUse`, `PostToolUse`, `PermissionRequest`, `UserPromptSubmit`, `Stop`, `PostCompaction`, `SessionStart`, `SessionEnd`. Hook type is `command` (shell) or `prompt` (LLM). Command hooks receive `{hook_event_name, tool_name, tool_input, session_id, prompt_id}` on stdin and may write `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": "..."}}` to stdout. Exit code `2` blocks; other non-zero codes are logged as errors without blocking.

## Confirmed `SKILL.md` frontmatter

`name`, `description`, `allowed-tools` (list), `triggers` (user and/or model — see residual risk below). Optional `subagent: true` runs the skill as a subagent.

## Residual risk / unverified detail

- The exact sub-schema of `SKILL.md`'s `triggers` frontmatter field (user vs. model trigger split) is not fully documented publicly as of this date. This implementation renders `triggers` as a flat YAML list, a conservative superset that should remain forward-compatible. Re-verify before the next plugin schema version bump.
- Plugin update/version-resolution semantics (`devin plugins update`) are only partially documented; not relied upon by this implementation, which produces an unpublished local bundle only.
- This note is a point-in-time snapshot. Devin's extensibility docs may change; re-verify against the sources above before relying on this schema for a new release.
