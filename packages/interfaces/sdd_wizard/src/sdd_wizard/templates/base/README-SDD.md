# SDD Setup & Guidelines

This project follows [SDD (Specification-Driven Development)](https://github.com/SergioLacerda/sdd-harness).

## Quick Start

1. Read the mandates: `cat .sdd/CANONICAL/mandate.spec`
2. Review guidelines: `ls .sdd-guidelines/`
3. Follow the commit protocol below
4. Run tests: `make test` or equivalent

## Commit Protocol (P003)

**Golden Rule: Agents propose, Humans dispose.**

When working with an AI agent:

| Action | Agent | Human |
|---|---|---|
| Write code / edit files | ✅ | — |
| Suggest commit message | ✅ | — |
| Execute `git commit` | ❌ | ✅ |
| Execute `git push` | ❌ | ✅ |
| Merge pull requests | ❌ | ✅ |

The agent stages changes and presents the exact command. The human reviews the diff and executes.

See full protocol: [SDD Harness — Commit Protocol](https://sergiolacerda.github.io/sdd-harness/spec/guides/commit-protocol/)

## Mandates (Hard Rules)

See `.sdd/CANONICAL/mandate.spec` - these are immutable.

## Guidelines (Best Practices)

See `.sdd-guidelines/` - organized by topic:
- git.md - Git workflow guidelines
- testing.md - Testing strategies
- naming.md - Naming conventions

## Customize (v3.2+)

Create `.sdd-custom/` to override guidelines locally.
