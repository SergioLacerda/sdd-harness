# SDD Governance Projection for Devin

Generates a self-contained, distributable Devin plugin bundle from this repository's
`.sdd/skills/` registry, in **Soft/Standalone** profile.

## What Soft/Standalone means

- Works without SDD Harness, without network, without any runtime Python/Go/Node dependency.
- Reports `policy_source=embedded_snapshot` and `assurance=reduced` — both in `AGENTS.md`
  (always loaded) and via a `SessionStart` hook that injects the same disclosure into the
  agent's context at session start.
- Is never represented as equivalent to a connected, Hard/Connected SDD Harness session.

Hard/Connected mode (a live SDD Harness probe/handshake) is **not implemented**. It requires
a separate RFC — see `docs/spec/guides/RFC_PROCESS.md` — because it would introduce a new SDD
external integration protocol.

## Build

```bash
sdd devin build
# optional: sdd devin build --dest ./some/other/path
```

Or from Python:

```python
from sdd_adapters.devin import DevinPluginGenerator

DevinPluginGenerator().generate(output_dir=repo_root)
```

Output: `dist/devin-plugin/` (gitignored — treat like any other build artifact).

## Install into Devin

```bash
devin plugins install ./dist/devin-plugin
```

## Bundle contents

| Path | Role |
|---|---|
| `.devin-plugin/plugin.json` | Plugin manifest (name, version, license, skill paths) |
| `AGENTS.md` | Always-on assurance/precedence disclosure |
| `skills/{name}/SKILL.md` | One per canonical SDD skill in `.sdd/skills/registry.json` |
| `hooks.json` + `hooks/session-start-assurance.sh` | Injects the Soft/Standalone disclosure into every session |
| `metadata/provenance.json` | Plugin version, compiler version, source revision, embedded policy digest, profile |
| `LICENSE` | Copied from the source project's root `LICENSE`, if present |

## Precedence order

1. Provider or organization safety controls (Devin's own permissions/config).
2. Connected SDD hard policy (not active in Soft/Standalone).
3. Project canonical policy (the consuming project's own `.sdd/`, if present).
4. Embedded SDD snapshot (this plugin's `skills/`).
5. Provider local rules (`.devin/config.json`, project `AGENTS.md`, `rules/`).
6. User task instructions.

## Canonical source

This plugin is a generated projection, never a policy source. Canonical SDD governance stays
in this repository's `.sdd/`. See `metadata/provenance.json` in a built bundle for the exact
source revision it was generated from.

## Known limitations

- `SKILL.md`'s `triggers` frontmatter sub-schema is rendered as a flat list — Devin's exact
  user/model trigger split was not fully documented publicly as of 2026-08-17. Re-verify
  against `docs.devin.ai/cli/extensibility/skills/creating-skills` before the next schema bump.
  See `docs/spec/guides/devin-plugin-provider-surface-evidence.md`.
- Hard/Connected mode is out of scope (see above).
- The plugin bundle has been verified structurally and against the real `.sdd/skills/`
  registry, but has not yet been installed into a live Devin CLI session. Run
  `devin plugins install ./dist/devin-plugin` against an actual Devin CLI installation
  before treating this as production-ready.
