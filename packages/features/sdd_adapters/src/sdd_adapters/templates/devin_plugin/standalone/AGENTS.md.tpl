# Project Rules

Ruleset version: `{{ standalone_ruleset_version }}`

This project defines its working rules in `.devin/rules/`. Read the file relevant to your current task before making changes:

- [`architecture.md`](.devin/rules/architecture.md) — function/file size, naming, typing, dependency direction
- [`git-safety.md`](.devin/rules/git-safety.md) — what you may and may not do with git
- [`testing.md`](.devin/rules/testing.md) — write the test first
- [`generated-artifacts.md`](.devin/rules/generated-artifacts.md) — never hand-edit generated output
- [`python.md`](.devin/rules/python.md) — Python-specific style, anti-patterns, tooling
- [`go.md`](.devin/rules/go.md) — Go-specific style, anti-patterns, tooling
- [`documentation.md`](.devin/rules/documentation.md) — what a comment is for

Permissions and lifecycle hooks are configured in `.devin/config.json` and `.devin/hooks.v1.json`.

These files are a generated starting point. Edit them directly to fit this project — there is no external source they must stay in sync with.
