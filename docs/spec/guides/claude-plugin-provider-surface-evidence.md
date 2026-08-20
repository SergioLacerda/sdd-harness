# Claude Code Provider Surface — Verification Evidence

**Verified:** 2026-08-19
**Verified by:** live web search + fetch against `code.claude.com` (Claude Code's
official documentation host) and `platform.claude.com`. Same due-diligence pattern
as `docs/spec/guides/devin-plugin-provider-surface-evidence.md` and
`docs/spec/guides/copilot-plugin-provider-surface-evidence.md`.

## Sources

- [Plugins reference](https://code.claude.com/docs/en/plugins-reference) — full
  plugin directory structure, `plugin.json` schema, hooks configuration format,
  installation scopes, `settings.json` plugin fields, skills-directory plugins,
  CLAUDE.md-vs-plugin-instructions precedence.
- [Settings](https://code.claude.com/docs/en/settings) — `.claude/settings.json`
  file locations and scope (`user`/`project`/`local`/`managed`), `permissions`
  block format and evaluation order, hooks lifecycle events.
- [Configure permissions](https://platform.claude.com/docs/en/agent-sdk/permissions) —
  permission rule format (`"ToolName(argument pattern)"`), deny → ask → allow
  evaluation order, corroborating the `settings.json` permissions shape.

## Confirmed customization surface (plain project config, not an installable plugin)

```text
CLAUDE.md                    # project root; read as persistent context at session start
.claude/
├── rules/
│   └── {topic}.md           # loaded per the InstructionsLoaded hook event
│                             # ("When CLAUDE.md or .claude/rules/*.md loaded")
├── settings.json            # team-shared (version-controlled)
└── settings.local.json      # personal overrides (gitignored)
~/.claude/settings.json      # user-wide settings
```

`.claude/settings.json` (or `~/.claude/settings.json` for user scope) supports, among
other fields:

- `permissions.allow` / `permissions.deny` — declarative rule list, format
  `"ToolName(argument pattern)"` (e.g. `"Read(**)"`, `"Bash(npm run *)"`,
  `"Bash(rm -rf *)"`). Evaluation order: deny → ask → allow; a deny rule blocks even
  in bypass-permission modes.
- `hooks` — lifecycle event hooks (`SessionStart`, `PreToolUse`, `PostToolUse`, and
  many more; see the Plugins reference for the full event list). `SessionStart` runs
  once per session and is commonly used to load context (e.g. recent git history).

Distinct, separate surface (not part of the plain project-config form above): a full
installable **plugin** — `.claude-plugin/plugin.json` manifest, `commands/`,
`agents/`, `skills/`, `hooks/hooks.json`, marketplace registration via
`.claude-plugin/marketplace.json`. `CLAUDE.md` at a *plugin's* root is explicitly
**not** loaded as project context — plugins provide instructions through skills,
agents, and hooks instead. This bundle form is out of scope for the standalone
project-config generator this note supports (see
`.analysis/refined/20260819-claude-standalone/proposal.md` Decision D-1).

## Confirmed structural parity versus Devin's standalone surface

Unlike GitHub Copilot (see `copilot-plugin-provider-surface-evidence.md`'s two
confirmed structural gaps — no lifecycle-hook mechanism, no declarative permissions
file), Claude Code's real standalone-relevant surface has a direct equivalent for
every element of Devin's standalone bundle:

| Devin (`.devin/` standalone) | Claude Code equivalent |
|---|---|
| `AGENTS.md` (always-on context) | `CLAUDE.md` (always-on context, read at session start) |
| `.devin/rules/*.md` (7 topic files) | `.claude/rules/*.md` |
| `.devin/config.json` `permissions.allow`/`deny` | `.claude/settings.json` `permissions.allow`/`deny` |
| `.devin/hooks.v1.json` (plugin-bundle only, single `SessionStart` event) | `.claude/settings.json` `hooks` block (many more lifecycle events) — **not used** in the standalone generator by design; see Decision D-2 below |

No structural-gap disclosure section is needed in the generated `CLAUDE.md` the way
Copilot's generated output needs one.

## Residual risk / unverified detail

- Claude Code's plugin/settings surface is documented as actively evolving —
  version-gated fields (e.g. a `plugin.json` field noted as requiring a specific
  Claude Code version) were observed during this search pass. Re-verify this note
  before the next standalone schema version bump, the same policy already applied
  to the Devin and Copilot evidence notes.
- Whether `.claude/rules/*.md` supports any form of per-file, path-scoped loading
  (the way Copilot's `.github/instructions/*.instructions.md` uses an `applyTo`
  glob frontmatter) was **not** confirmed by this search pass — the fetched
  Plugins reference page documents frontmatter for plugin `skills/`/`agents/`
  files, not for `.claude/rules/*.md`. Treat `.claude/rules/*.md` as always loading
  in full for the session until a targeted follow-up check against
  `code.claude.com/docs/en/settings` (or an equivalent first-party page) confirms
  otherwise. This gates the exact template/frontmatter shape of the standalone
  generator's `.claude/rules/*.md` output — see
  `.analysis/refined/20260819-claude-standalone/tasks.md` TASK-5.
- This bundle has been verified structurally only — it has not yet been generated
  or tested inside a real Claude Code session. Generate it and confirm Claude Code
  picks up `CLAUDE.md` / `.claude/rules/*.md` / `.claude/settings.json` as expected
  before treating this as production-ready.
- Precedence of a `permissions` block across `user` → `project` (`.claude/settings.json`)
  → `local` (`.claude/settings.local.json`) scopes was corroborated (managed >
  CLI `--settings` > user, per the Plugins reference's `pluginConfigs` precedence
  note) but not independently re-verified against the general (non-plugin)
  `settings.json` precedence page in this search pass — worth a direct check
  before relying on scope-merge behavior in generated content.
