# Landing Page — Nav Order, External-Link Glyph, Image/Text Layout Fixes

> Spec. Produced by Strategist mission `20260907-landing-nav-layout-tweaks` (refined package:
> `.analysis/refined/20260907-landing-nav-layout-tweaks/`). This document is a spec for a
> subsequent coding task — it does not itself change any file under `apps/landing/`.

## 1. Nav order + external-link glyph (`SiteNav.astro`)

New order: **Detalhe técnico, Instalação, Selector** (Selector and Instalação swap; Selector
moves last). Add an ↗ glyph next to Selector only — it's the one nav item that doesn't point
at a real page on this site yet (`href="#"` placeholder), unlike Detalhe técnico and
Instalação, which are real internal Astro routes.

```html
<div class="navlinks">
  <a href={`${BASE_URL}detalhe-tecnico`} ...>{nav.detalheTecnico}</a>
  <a href={`${BASE_URL}instalacao`} ...>{nav.instalacao}</a>
  <a href="#">
    <span data-i18n="selector">{nav.selector}</span> <span aria-hidden="true">↗</span>
  </a>
</div>
```

- ↗ was chosen over 🔗/⧉ — it's the glyph the pre-migration `Landing.tsx` already used for its
  own external "Docs" link, so this stays consistent with an established convention already
  in this codebase.
- `aria-hidden="true"` on the glyph span — it's decorative; screen readers should read the
  link text, not "up-right arrow."

**Risk to handle carefully:** `SiteNav.astro`'s own `<script>` (`applyLang()`) updates
`el.textContent` on `[data-i18n]` elements when the language toggles. Today `data-i18n` sits
directly on the `<a>` tag. If the glyph span were added as a sibling inside that same `<a>`
without moving `data-i18n`, the lang-switch script would overwrite `el.textContent` on the
whole `<a>` and silently delete the glyph on every toggle. Fix: move `data-i18n="selector"`
onto an inner `<span>` wrapping only the label text (as shown above), so the lang-switch script
only replaces that inner span's content, leaving the glyph span untouched.

## 2. `VirtuesWheel.astro` — keep side-by-side down to a narrower width

Today, `.virtues-layout` (`display:flex; flex-wrap:wrap; gap:72px`) combines a fixed
`.cycle-diagram` (`flex:0 0 420px`) with `.virtue-panel` (`flex:1 1 320px`) — combined minimum
width ≈ 812px. Below that, `flex-wrap:wrap` naturally stacks the panel under the diagram, and
an explicit `@media(max-width:900px){.cycle-diagram{flex-basis:100%}}` forces it even more
aggressively. This causes stacking at the ~581px viewport width reported (screenshot
evidence), where side-by-side was expected instead.

Replace the single breakpoint with two tiers — shrink-but-stay-side-by-side first, true
stacking only as a last resort for very narrow phones:

```css
.virtues-layout {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 72px;
  flex-wrap: wrap;
}
.cycle-diagram { width: 100%; max-width: 420px; display: block; flex: 0 0 420px; }

@media (max-width: 900px) {
  .virtues-layout { gap: 40px; }
  .cycle-diagram { flex: 0 0 240px; max-width: 240px; }
  .virtue-panel { flex: 1 1 220px; }
}
@media (max-width: 420px) {
  .cycle-diagram { flex-basis: 100%; max-width: 300px; margin: 0 auto; }
}
```

- The old rule that forced full-width stacking at 900px is replaced with a **shrink** rule
  instead — diagram and gap both get smaller so the combined minimum width (240 + 40 + 220 ≈
  500px) comfortably fits the ~581px viewport tested, keeping the row layout.
- The second breakpoint (≤420px) is a deliberate fallback for phones narrower than what was
  tested — below that width even a 240px diagram plus readable text won't fit a row
  comfortably, so it stacks (diagram full-width, capped at 300px).
- **For the implementer:** verify visually at common device widths (375px, 390px, 414px) and
  adjust the two breakpoint values if the shrink tier still feels cramped — the pixel values
  above are a starting point, not a hard requirement. `.virtue-panel`'s text sizing (`.vname`
  26px, body 14.5px) is untouched; if it reads too large at the 240px-diagram tier, treat that
  as a follow-up, not a blocker.

## 3. `RuntimeProof.tsx` — both custody-seal legends to the right

Today the row is `[mandate-legend, right-aligned] [circle] [guideline-legend, left-aligned]` —
one legend on each side of the seal image. Change to `[circle] [both legends, stacked,
left-aligned, to its right]`:

```tsx
<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 22, marginBottom: 40 }}>
  <svg width={110} height={110} viewBox="0 0 200 200" aria-hidden="true">
    {/* unchanged */}
  </svg>
  <div style={{ display: 'flex', flexDirection: 'column', gap: 14, textAlign: 'left' }}>
    <div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>
        {withGovernanceStats(stats, 'M001–M{{MCOUNT}}')}
      </div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', color: 'var(--ink-faint)', textTransform: 'uppercase', marginTop: 2 }}>
        {c.legendMandate}
      </div>
    </div>
    <div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>
        {withGovernanceStats(stats, 'G01–G{{GCOUNT}}')}
      </div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', color: 'var(--ink-faint)', textTransform: 'uppercase', marginTop: 2 }}>
        {c.legendGuideline}
      </div>
    </div>
  </div>
</div>
```

- Both legend blocks move from independent right/left `textAlign` to a shared
  `flexDirection:'column'` container, both left-aligned, `gap:14` between them — reads as one
  grouped label to the seal's right.
- The SVG circle markup itself is unchanged — only its position in the row (now first) and the
  legend grouping change.
- The parent `<section>` is still `textAlign:'center'` as a whole, so the circle+legend-group
  pair sits centered together as a unit — same overall visual weight as before, just re-flowed
  internally.

## What stays unchanged / explicitly out of scope

- Detalhe técnico's and Instalação's hrefs/behavior — only their relative order moves.
- Selector's destination (`href="#"`) — still a placeholder; only its visual affordance
  changes.
- The `IntersectionObserver`/`goTo` scroll-nav logic — untouched.
- `RuntimeProof`'s steps list — confirmed with the user as already correct (icon-left,
  text-right); it was reference evidence in the screenshots, not a second bug.
- `detalhe-tecnico.astro`'s own content/layout — untouched.

## Validation for the coding task

- Nav order correct visually and in DOM; toggling BR/EN still shows the ↗ glyph after
  switching (the `data-i18n` placement risk above must be handled, not just the reorder).
- Visual check at ~581px (screenshot 1's width): `VirtuesWheel` diagram and text panel stay
  side-by-side. Visual check at ~375–414px: stacked fallback is acceptable there.
- `RuntimeProof`: both legends render stacked, left-aligned, to the seal's right;
  `RuntimeProof.test.tsx` still passes or is updated if it asserts on the old DOM structure.
- `npm run build`, `npm run lint`, `npm run test` all pass.
