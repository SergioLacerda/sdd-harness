# Landing Page Migration to the Providentian Design

> Migration specification. Produced by Strategist mission `20260907-landing-page-providentia-migration`
> (refined package: `.analysis/refined/20260907-landing-page-providentia-migration/`). This document
> is a spec for a subsequent coding task — it does not itself change any file under `apps/landing/`.

## Status caveats (read first)

- **Sequencing caveat.** The two source documents this migration is based on
  (`.analysis/pending/ACHADOS_E_MELHORIAS_PROVIDENTIA.md`, `.analysis/pending/nova_arquitetura.txt.txt`)
  both treat the "Providentian Agent Governance" identity as a **proposal**, and the second one
  explicitly recommends renaming public-facing surfaces — including the landing page — as the
  **last** step of a much larger backend migration (Governed Intake, Execution Contract, Context
  Broker), not the first. This migration proceeds ahead of that recommended sequencing, as an
  explicit, informed choice made when this spec was refined. It does not imply the naming ADR
  (tracked separately, see below) has been written or approved.
- **Naming caveat.** Final package/repository naming (`sdd-harness-landing` vs. a Providentian
  equivalent) is unresolved. This spec does not change `apps/landing/package.json`'s `name`
  field, and any Providentian-branded install command shown on the `instalacao` page should be
  presented as illustrative of the target UX, not the current real CLI entrypoint.
- **Related, not included, follow-up work:** a naming/rebrand ADR, and the backend architecture
  rework described in the source documents. Both are tracked as separate, independent efforts.

## Source material

- `.analysis/pending/ACHADOS_E_MELHORIAS_PROVIDENTIA.md` — architecture findings, P0–P3 roadmap
- `.analysis/pending/nova_arquitetura.txt.txt` — product identity, four-virtue model, phased migration plan
- `.analysis/pending/design_handoff_providentia/` — static Astro 4 design handoff (3-page structure, bronze/dark tokens)
- Live app: `apps/landing/` (Astro 7 + React 19, `sdd-harness-landing`)

## Target page structure

The live app currently has **one** route rendering a single React island. The target is
**three** routes, matching the design handoff's information architecture, kept on the live
app's Astro-with-React-islands pattern (not a rewrite to the handoff's zero-React static shape):

```
apps/landing/src/pages/
├── index.astro            # Home / Virtudes — existing entry point, restructured
├── detalhe-tecnico.astro  # NEW — executive-summary architecture explainer
└── instalacao.astro       # NEW — install/CLI instructions
```

```
                    CURRENT                                   TARGET
        ┌─────────────────────────┐          ┌─────────────────────────────────────┐
        │  index.astro            │          │  index.astro (home/virtudes)         │
        │  └─ Landing.tsx         │   ───▶    │  detalhe-tecnico.astro (NEW)         │
        │     (single big island) │          │  instalacao.astro (NEW)              │
        └─────────────────────────┘          └─────────────────────────────────────┘
```

## Content & component mapping

| Handoff source (static Astro) | Target treatment in `apps/landing` | Notes |
|---|---|---|
| `src/layouts/BaseLayout.astro` | Merge into existing `apps/landing/src/layouts/BaseLayout.astro` | Adopt new `<head>`/font/token-import shape; keep existing SEO/meta conventions already in the live layout. |
| `src/styles/tokens.css` (bronze/dark palette) | Replace/extend `apps/landing/src/styles/tokens.css` | Live app already separates `tokens.css` from `global.css` — same seam, just new values. Diff against current token usage in `Landing.tsx`/`GovernanceFooter.tsx`/`Terminal.tsx` before removing any current token. |
| `src/styles/global.css` (nav/section/table styles) | Merge into `apps/landing/src/styles/global.css` | Additive — diff against existing shared styles, don't blindly overwrite. |
| `src/components/SiteNav.astro` (fixed header, BR/EN toggle, GitHub icon) | New component in `apps/landing/src/components/` | Live app currently has no persistent nav (single page). Wire the BR/EN toggle into the existing `i18n.ts` `Lang` mechanism — don't duplicate the logic. Confirm first whether the handoff's toggle is functional or a static placeholder (open question, see below). |
| `src/components/BrandLogo.astro` (animated logo mark) | New component | Static SVG/CSS animation, no data dependency — direct port. |
| `src/components/VirtuesWheel.astro` (interactive SVG selector, `VIRTUES` array as content source) | New component; `VIRTUES` content sourced from `nova_arquitetura.txt.txt` §2's virtue table | Becomes the anchor content block of `index.astro`. Open decision: does the current `Landing.tsx` terminal-demo/step content get folded in below the virtues wheel, or move to `detalhe-tecnico.astro`? Recommendation: keep the live-stats demo on the entry page — it's the current page's strongest asset and has no equivalent in the static handoff. |
| `src/components/ScrollSectionNav.astro` (side dot-nav + scroll-spy) | New component, reused across all 3 pages | IntersectionObserver port; wire `sectionIds` per page. |
| `src/components/InstallCard.astro` (copy-to-clipboard command block) | New component for `instalacao.astro` | Use real, current install path/CLI name — not the handoff's `providentian/providentian-agent-governance` placeholders — per the naming caveat above. |
| `src/pages/index.astro`, `detalhe-tecnico.astro`, `instalacao.astro` | Replace live `index.astro`; add the two new routes | See page-by-page plan below. |

## Page-by-page plan

### `index.astro` — Home / Virtudes

- Keeps the site's primary entry-point role.
- Leads with `BrandLogo` + `SiteNav`.
- Primary content block: `VirtuesWheel` (Providentia / Prudentia / Diligentia / Fidelitas).
- Open decision: fold the existing `Landing.tsx` terminal-demo/live-stats content in below
  the virtues wheel (recommended), or move it to `detalhe-tecnico.astro`.

### `detalhe-tecnico.astro` — Executive-summary architecture explainer

Not a reproduction of the source architecture documents — a simplified, accessible version
for landing-page visitors. Draft copy:

```markdown
## How it works

[Interfaces] → [Governed Intake] → [Context Broker] → [Capability Runtime] → [Governance Assurance]
     ↑                                                                              │
     └──────────────────────── learning & drift feedback ─────────────────────────┘

- **Interfaces** — however you talk to it: CLI, hook, slash command.
- **Governed Intake (Providentia)** — figures out what you're asking, how risky it is,
  and what it needs to know before doing anything.
- **Context Broker** — gathers just enough evidence, nothing more.
- **Capability Runtime (Diligentia)** — does the actual work, inside limits.
- **Governance Assurance (Fidelitas)** — checks the result stayed faithful to what you asked.

## The four virtues

| Virtue | In plain terms |
|---|---|
| Providentia | What could happen, and what do we need to know first? |
| Prudentia | What's allowed, and through which path? |
| Diligentia | How do we execute carefully, within limits? |
| Fidelitas | Did the result stay true to the intent? |
```

Final wording is an editorial pass during implementation — this draft is a starting point, not
frozen copy.

### `instalacao.astro` — Install / CLI

- `InstallCard` blocks using the real, current install path — not the handoff's placeholder
  package name. Any Providentian-branded command (e.g. `provident "..."`) shown here should be
  clearly marked as illustrative of the target UX (per `ACHADOS_E_MELHORIAS_PROVIDENTIA.md` §5.1),
  not the current real CLI entrypoint — the CLI rename itself is a separate, later effort.

## What must not silently break

- **Live governance stats.** `loadGovernanceStats()` (fingerprint, mandate counts) is currently
  wired into `index.astro`/`Landing.tsx` via `apps/landing/src/lib/governance-data.server.ts` and
  `governance-stats.ts`. Decide explicitly which of the 3 new pages consumes it — recommendation:
  keep it on `index.astro`.
- **Bilingual i18n.** `apps/landing/src/lib/i18n.ts` (`Lang = 'pt' | 'en'`) already exists and is
  tested. The new `SiteNav`'s BR/EN toggle must drive this mechanism, not a new parallel one.
- **Existing tests.** `governance-data.server.test.ts` and `governance-stats.test.ts` must keep
  passing. Whether/how `lint`/`cover` scope extends to the new 3-page structure is an open
  decision for the coding task, not something to silently drop.

## Open decisions left to the coding task

- Whether the handoff's BR/EN toggle logic is reusable as-is or needs to be built against
  `i18n.ts` from scratch (read `SiteNav.astro` directly to resolve).
- Test/lint scope for the new 3-page structure.
- Whether `apps/landing/package.json`'s `name` field changes — left untouched by this spec.
- Whether `Landing.tsx`'s existing terminal-demo content is folded into `index.astro` below the
  virtues wheel, or relocated — recommendation given above, not mandated.

## Out of scope for this document

This spec does not itself modify `apps/landing/src/**`, `apps/landing/public/**`, or
`apps/landing/package.json`. Implementing the plan above (porting pages, components, and
styles) is a separate coding task, tracked as `implementation_handoff` items in the Strategist
mission's `tasks.md` (`.analysis/refined/20260907-landing-page-providentia-migration/tasks.md`).
