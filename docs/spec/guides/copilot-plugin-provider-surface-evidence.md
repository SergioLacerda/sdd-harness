# GitHub Copilot Provider Surface — Verification Evidence

**Verified:** 2026-08-18
**Verified by:** live web search against `docs.github.com`, `github.blog`, and Microsoft's `devblogs.microsoft.com` (no pinned local fixture existed prior to this note). Same due-diligence pattern as `docs/spec/guides/devin-plugin-provider-surface-evidence.md`.

## Sources

- [Adding repository custom instructions for GitHub Copilot](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot) — `.github/copilot-instructions.md` scope (completions, Chat, PR reviews).
- [Copilot coding agent now supports AGENTS.md custom instructions](https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/) — root/nested `AGENTS.md` support, nearest-file-wins precedence, coding-agent scope.
- [Support for different types of custom instructions](https://docs.github.com/en/copilot/reference/custom-instructions-support) — `.github/instructions/*.instructions.md`, `applyTo` glob matching and per-request merge behavior.
- [GitHub Copilot coding agent now supports .instructions.md custom instructions](https://github.blog/changelog/2025-07-23-github-copilot-coding-agent-now-supports-instructions-md-custom-instructions/)
- [Your first prompt file](https://docs.github.com/en/copilot/tutorials/customization-library/prompt-files/your-first-prompt-file) — `.github/prompts/*.prompt.md`.
- Chat modes (`.github/chatmodes/*.chatmode.md`): corroborated across multiple third-party write-ups (NashTech, Medium/Nived Velayudhan, Arinco) describing the same directory convention; no single GitHub Docs canonical page was pinned for this specific item in this search pass — treat chat-mode directory placement as `corroborated_inference`, not `explicit`, until cross-checked against a first-party GitHub Docs page.
- [Configure the development environment for GitHub Copilot coding agent](https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment) — `.github/workflows/copilot-setup-steps.yml`.

## Confirmed customization surface

```text
.github/
├── copilot-instructions.md        # always-on: completions + Chat + PR review
├── instructions/
│   └── {topic}.instructions.md    # path-scoped via `applyTo` glob frontmatter
├── prompts/
│   └── {name}.prompt.md           # explicitly invoked via /{name} in chat
├── chatmodes/
│   └── {name}.chatmode.md         # custom persona/tool/response-format bundle
└── workflows/
    └── copilot-setup-steps.yml    # coding-agent sandbox environment provisioning
AGENTS.md                          # repo root; also natively read by Copilot coding agent
                                    # (nested AGENTS.md supported, nearest wins)
```

`.github/instructions/*.instructions.md` without an `applyTo` key behaves like
`applyTo: "**"`. On every request, Copilot evaluates every instructions file's
`applyTo` against files currently in context and merges all matching layers — no
restart or reload is needed after editing an instructions file.

## Confirmed structural gaps versus Devin's standalone surface

Devin's standalone bundle (`AGENTS.md` + `.devin/config.json` + `.devin/hooks.v1.json`
+ `.devin/rules/*.md`) has two elements with **no confirmed Copilot equivalent** as of
this search pass:

1. **Lifecycle hooks.** Devin's `.devin/hooks.v1.json` (e.g. a `SessionStart` hook
   receiving JSON on stdin, returning `additionalContext` on stdout) has no
   documented Copilot counterpart. Copilot's customization surface is static files
   read at request time (instructions/prompts/chat modes); no runtime hook API was
   found.
2. **Declarative config/permissions file.** Devin's `.devin/config.json` has no
   documented Copilot counterpart. `copilot-setup-steps.yml` is the closest named
   file, but it configures the coding agent's *build/CI sandbox environment*
   (tools, runtimes, dependencies installed before a background task starts), not
   agent behavior, governance policy, or tool permissions — a different concern
   entirely, not a partial match.

A standalone Copilot generator must disclose both gaps explicitly in its always-on
output file, not silently omit them or substitute an invented file Copilot would not
actually read.

## Residual risk / unverified detail

- Precedence order when `.github/copilot-instructions.md`, root `AGENTS.md`, and
  matching `.github/instructions/*.instructions.md` files are simultaneously present
  is not fully documented publicly as of this date. Until clarified, a standalone
  generator should treat `.github/copilot-instructions.md` as the single primary
  always-on file and avoid emitting a root `AGENTS.md` with overlapping content by
  default (see `docs/plans/2026-08-18-copilot-governance-projection-soft-standalone.md`
  for the resulting design decision).
- `.github/chatmodes/*.chatmode.md` directory placement is corroborated by secondary
  sources only in this search pass, not a pinned first-party GitHub Docs page — worth
  a direct-source re-check before any future work emits chat-mode files.
- Re-verify this whole surface before the next plugin/standalone schema version bump,
  the same policy already applied to the Devin evidence note.
