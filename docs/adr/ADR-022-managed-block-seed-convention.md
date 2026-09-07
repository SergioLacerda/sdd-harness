# ADR-022 - Managed-Block Convention for Shared-Namespace Seed Files

**Status:** Accepted
**Date:** 2026-09-06
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

sdd generates root-level onboarding/redirector files — `CLAUDE.md`,
`GEMINI.md`, `AGENTS.md` — whose filenames are conventions independently
recognized by other AI coding tools (Claude Code, Gemini CLI, and an
emerging cross-tool `AGENTS.md` standard), not sdd-exclusive namespaces.
Generation of each is an independent, wizard-selectable choice
(`IntelligentSeedlingsGenerator.generate_all(selected=...)`), so whether a
given repository ends up with any of them committed reflects an accidental
past selection, not a designed contract.

Two related problems were found while investigating why a `pre-push` git
hook blocked a push over a stale `CLAUDE.md` fingerprint
(`.analysis/refined/20260906-root-seed-githook-necessity/`):

1. The three generators (`generate_claude_seed`, `generate_gemini_seed`,
   `generate_agents_md`) performed an unconditional whole-file overwrite —
   no merge, no preservation of anything else in the file. A human, another
   AI agent, or another tool adding its own content to the same file would
   have that content silently destroyed on the next `sdd` regeneration.
2. `check_root_seed_drift` validated the entire file's content by
   implication (any fingerprint-line mismatch anywhere in the file failed
   the whole file), with no way to distinguish "sdd's own content drifted"
   from "someone else's unrelated edit happened to be nearby."

Neither the writer nor the validator could distinguish "content sdd itself
generated" from "content something else added to the same file," because no
such distinction existed in the file format.

## Decision

Introduce a **managed-block convention**: sdd-generated content in a
shared-namespace file lives inside a single delimited region,

```
<!-- sdd:managed:begin -->
...sdd-generated content, including the fingerprint header...
<!-- sdd:managed:end -->
```

- **Writers** (`generate_claude_seed`, `generate_gemini_seed`,
  `generate_agents_md`) read-merge-write: locate the existing block if
  present, replace only its interior, leave everything else in the file
  untouched. A file with no block gets one inserted at the top (existing
  content preserved below it); a not-yet-existing file is created with just
  the block.
- **Validators** (`check_root_seed_drift`) extract and check only the
  block's interior. A file with no managed block is `unmanaged` — sdd makes
  no claim over content it never delimited as its own, so this never fails
  the check.
- **Malformed markers fail closed on the write path**: unbalanced or
  duplicated markers raise `MalformedManagedBlockError`, caught by each
  generator as its own failure (`return False`, logged). The writer never
  falls back to a whole-file overwrite on this error — that would silently
  destroy whatever the markers were protecting, defeating the convention's
  purpose. The read/validate path degrades safely instead: malformed
  markers are treated the same as absent markers (`unmanaged`), since a
  validator reading an arbitrary, possibly hand-edited file must not crash.

Implementation: `sdd_core.utils.managed_block`
(`merge_managed_block`, `extract_managed_block`,
`MalformedManagedBlockError`) — placed in `sdd_core` because both
`sdd_wizard` (writers) and `sdd_cli` (validator) already declare
`sdd-core>=1.0` as a dependency, so no new cross-package dependency was
introduced.

## What This Replaces

An earlier draft of this same investigation proposed branching enforcement
severity on git-tracked status (tracked files block `pre-push`; untracked
files only warn). That approach was rejected before implementation once
wizard-selectable generation (see Context) showed tracked status reflects
an accidental past choice, not a designed contract — an unreliable axis to
hang enforcement on. The managed-block convention replaces that mechanism
entirely: enforcement now keys on content ownership (is there a managed
block, and is it stale), never on git history.

## Scope

Implemented for `CLAUDE.md`, `GEMINI.md`, `AGENTS.md` — the three
generator keys among the wizard's ~17 that are root-level, cross-tool
convention filenames (as opposed to sdd-exclusive paths like
`.sdd/seedlings/*.json`, or tool-specific subdirectories like `.vscode/`,
`.cursor/rules/`). `sdd_core.utils.managed_block`'s implementation is
format-agnostic by design specifically so it can be reused for other
generator keys without redesign; wiring those is deferred (see
`.analysis/todo/riposte-captures.md`, mission_ref
`20260906-root-seed-githook-necessity`) rather than done in this change.

## Consequences

- A stale managed block in any of the three files still fails
  `check_root_seed_drift`, regardless of tracked status — the original
  incident (a local-only `CLAUDE.md` blocking `git push`) is fixed by the
  file becoming `unmanaged` after this change ships (no markers yet), not
  by any tracked/untracked branch.
- Every already-deployed `CLAUDE.md`/`GEMINI.md`/`AGENTS.md` is `unmanaged`
  immediately after this ships (predates the marker convention) until the
  next wizard run adds markers. This is an intentional, gradual, silent
  migration — no forced one-time migration step was added.
- Future generator additions that write into a shared or ambiguous-ownership
  path should default to this convention rather than a whole-file
  overwrite, using `sdd_core.utils.managed_block` directly.

## Alternatives Considered

- **Track/untracked severity split** — rejected; see "What This Replaces."
- **Drop `CLAUDE.md`/`GEMINI.md`/`AGENTS.md` from drift checking entirely**
  — rejected; the embedded fingerprint can still mislead a human or agent
  reading the file locally regardless of whether it ever reaches a shared
  remote. Removing the check would silence a legitimate signal instead of
  correcting its scope.
- **Extend `sdd governance generate` to write root `CLAUDE.md`** — considered
  and deferred; crosses the `sdd_cli`/`sdd_wizard` package boundary and
  wasn't evaluated for side effects on the wizard's own idempotency
  assumptions. Out of scope for this change.

## Links

- `.analysis/refined/20260906-root-seed-githook-necessity/` — analysis,
  proposal, design, tasks for this decision
- Implementation: `packages/core/sdd_core/src/sdd_core/utils/managed_block.py`
- Consumers: `packages/interfaces/sdd_wizard/src/sdd_wizard/orchestration/seedlings/ai_seeds.py`,
  `.../seedling_renderer.py`,
  `packages/interfaces/sdd_cli/src/sdd_cli/services/governance_config_reader.py`
