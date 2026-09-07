# Fix Recommendation: `REPO_ROOT` Resolution in `governance-data.server.ts`

> Bug report + fix recommendation. Produced by Strategist mission
> `20260907-repo-root-resolution-bug-astro-build` (refined package:
> `.analysis/refined/20260907-repo-root-resolution-bug-astro-build/`). This document is a
> recommendation for a subsequent coding task — it does not itself change any file.

## Confirmed root cause

`apps/landing/src/lib/governance-data.server.ts` computes the monorepo root as:

```ts
const REPO_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../../..',
);
```

i.e. "go up exactly 4 directories from wherever this file's compiled module lives." This
assumption holds for the unbundled source file but breaks under `astro build`:

```
SOURCE (dev / vitest)                    BUILD (astro build)
apps/landing/src/lib/                    apps/landing/.astro/.prerender/chunks/
  governance-data.server.ts                governance-data.server_<hash>.mjs
  └─ 2 segments under apps/landing/        └─ 3 segments under apps/landing/
       (src, lib)                               (.astro, .prerender, chunks)

REPO_ROOT = 4 hops up from either location — correct for source (2 segments + 2 more
reaches sdd-harness/), one hop short for the build chunk (3 segments + only 1 more
hop remaining before REPO_ROOT is computed → lands on apps/, not sdd-harness/).
```

**Confirmed, not inferred**: reproduced locally by running `astro build` and reading the
actual emitted chunk file's on-disk path plus its (unmodified) `REPO_ROOT`/`METADATA_PATH`
computation. The resulting wrong path exactly matches the build-time warning:
`.sdd/metadata.json not readable at .../sdd-harness/apps/.sdd/metadata.json` — missing
exactly one `sdd-harness/` segment.

**Impact**: `output: 'static'` in `astro.config.mjs` means the static HTML is generated once,
at build time, with no runtime re-evaluation in production. Production builds silently ship
placeholder governance stats (`M001–M000`, fingerprint `—`) instead of real ones
(`M001–M016`, etc.) — no build error, just a console warning during the build step.

**Not a regression**: confirmed pre-existing — `git log` shows this file's only commit is the
original app-scaffolding commit (`4a2caaa`); no subsequent mission touched its logic.

## Recommended fix

Walk upward from `import.meta.url`'s directory until a `.git/` directory is found — that is
`REPO_ROOT`, independent of how deep the bundler nests the compiled chunk. Keep the existing
`.sdd/metadata.json` read (and its graceful fallback) as a separate, subsequent step:

```
1. Walk upward from import.meta.url's directory until a `.git/` directory is found
   → this is REPO_ROOT, independent of whether governance has been generated
2. Attempt to read <REPO_ROOT>/.sdd/metadata.json
   → existing graceful fallback (PLACEHOLDER_GOVERNANCE_STATS + warning) applies unchanged
   → this behavior is already correct; the bug was never here
```

Searching for `.sdd/metadata.json` itself (instead of `.git/`) was considered and rejected:
on a fresh checkout, before `sdd governance generate` has run, that file doesn't exist yet, so
the search would climb to filesystem root without finding anything and report a confusing
"couldn't find the repo" error instead of the correct, already-useful "found the repo,
governance isn't generated yet" warning. `.git/` decouples "finding the root" from "whether
governance was generated," which is the correct separation — and is the same convention used
by common "find repo root" utilities (`find-up`, `pkg-up`).

## Alternatives considered

| Option | Stable under Astro/Vite upgrades? | Stable under invocation changes? | Works before `.sdd/` exists? |
|---|---|---|---|
| **`.git/` marker search (recommended)** | Yes — doesn't depend on chunk depth | Yes — doesn't depend on cwd | Yes |
| `process.cwd()` | Yes | **No** — assumes cwd is always `apps/landing` (true today only because CI pins `working-directory: apps/landing` in `docs.yml`, `reusable-security.yml`, `ecosystem-canary.yml`) | Yes |
| Explicit `SDD_REPO_ROOT` env var | Yes | Yes, but only where someone remembers to set it (every CI job + every local dev script) | Yes |

`process.cwd()` was not preferred because, while more stable than the current bundler-depth
counting, it still embeds a fixed relational assumption that happens to hold today only
because of a CI convention — not something the fix needs to assume when the marker search
needs no such assumption at all.

An explicit env var was not preferred as the *primary* mechanism because it requires
remembering to set it in every build entry point. It remains a reasonable **complementary**
fallback: `process.env.SDD_REPO_ROOT ?? <result of the .git/ search>`.

## What this does not change

The existing graceful-fallback behavior when `.sdd/metadata.json` is genuinely absent
(`PLACEHOLDER_GOVERNANCE_STATS` + console warning) is correct today and is not part of the
bug — the recommendation preserves it unchanged, just feeds it a correct `REPO_ROOT`.

## Follow-up, not verified by this report

Whether real production deploys of `apps/landing` have actually been shipping placeholder
stats (as opposed to a CI environment that happens to avoid this specific failure) was **not**
verified here — this report confirms the mechanism via local reproduction, not the live
deployed site's HTML or CI build logs. Recommended as a follow-up check before or alongside
applying the fix.

## Scope

This report does not modify `apps/landing/src/lib/governance-data.server.ts`. Applying the
fix above is a separate coding task, tracked as an `implementation_handoff` item in the
Strategist mission's `tasks.md`
(`.analysis/refined/20260907-repo-root-resolution-bug-astro-build/tasks.md`).
