# Landing Page — Full-Height Sections + Enlarged Navigation Arrows

> Spec. Produced by Strategist mission `20260907-landing-fullheight-sections-nav` (refined
> package: `.analysis/refined/20260907-landing-fullheight-sections-nav/`). This document is a
> spec for a subsequent coding task — it does not itself change any file under `apps/landing/`.

## Scope

Applies to `index.astro` and `detalhe-tecnico.astro` — the two pages using the
`<section>` + `ScrollSectionNav` pattern. `instalacao.astro` doesn't use this pattern and has
nothing to change under either request.

## 1. Full-height sections

Change the shared `section` rule in `apps/landing/src/styles/global.css`:

```css
section {
  min-height: 100vh;
  padding: 88px 32px;
  border-bottom: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  justify-content: center;
  box-sizing: border-box;
}
```

- `min-height: 100vh`, not fixed `height` — `capacidades` (the `CapabilitiesPanel` 4-tab
  island on `detalhe-tecnico.astro`) can be taller than one viewport; a fixed height would
  clip it. `min-height` guarantees "at least one full screen" while letting taller sections
  grow naturally.
- `display:flex; flex-direction:column; justify-content:center` vertically centers each
  section's content within the now much taller box.
- `padding: 88px 32px` replaces `padding: 88px 0`. The horizontal `32px` was previously
  supplied by each section's own `.wrap`; adding it here too is harmless nesting, but verify
  visually and drop it here if it causes double-spacing with `.wrap`.
- `box-sizing: border-box` ensures padding doesn't push the box past `100vh`.
- `section:last-of-type { border-bottom: none; }` (already exists) is unchanged.
- **Keep the `border-bottom` divider** even at full height — with sections this tall, it still
  reads as a clean seam on scroll rather than clutter.

## 2. Enlarge the existing corner navigation arrows

**Design note:** an earlier draft of this spec moved the prev/next controls to new
viewport-centered buttons (top-center "previous", bottom-center "next"). That was **rejected
at the approval gate** — the user confirmed the existing bottom-right corner position and the
existing prev/next coverage are already sufficient; only visual prominence needed to change.
The design below reflects the accepted, revised version.

**Position, and the underlying navigation logic, are unchanged.** `ScrollSectionNav.astro`
already implements everything needed: a `current` section index, an `IntersectionObserver`-driven
`setActive(i)`, a `goTo(i)` that smooth-scrolls to the target section, and prev/next buttons
already wired with correct disabled-at-boundary state. This is a size/contrast change only, in
`apps/landing/src/components/ScrollSectionNav.astro`'s `<style>` block:

```css
.scrollarrows {
  position: fixed;
  right: 24px;
  bottom: 32px;
  z-index: 50;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.scrollarrows button {
  width: 52px;              /* was 34px */
  height: 52px;              /* was 34px */
  border-radius: 50%;
  border: 1.5px solid var(--bronze-dim);      /* was 1px var(--line-strong) — bronze-tinted at rest */
  background: var(--panel);                    /* was rgba(18,23,31,.85) — solid, not translucent */
  color: var(--ink);                           /* was var(--ink-dim) — higher contrast at rest */
  box-shadow: 0 4px 16px rgba(0,0,0,.35);       /* new — lifts it off the page */
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all .18s;
}
.scrollarrows button svg { width: 20px; height: 20px; }   /* was 14px */
.scrollarrows button:hover:not(:disabled) {
  border-color: var(--bronze);
  color: var(--bronze-bright);
  transform: scale(1.06);
}
.scrollarrows button:disabled { opacity: .28; cursor: default; }
@media (max-width: 760px) { .scrollarrows { display: none; } }
```

- Size ~1.5× (34px → 52px), icon 14px → 20px — reads as a primary control, not a corner
  afterthought.
- Border and icon color are bronze-tinted **at rest**, not only on hover, and the background
  goes from translucent to a solid `var(--panel)` fill — legible against any section
  background without needing a hover state to "activate" its visibility.
- `box-shadow` added to visually lift the control off the page.
- Position, `disabled`-at-boundary state, the mobile hide rule (`@media (max-width: 760px)`),
  and the underlying `goTo`/`setActive` script are all unchanged from what ships today.

## What stays unchanged

- The side dot markers (`.scrollnav`) — kept exactly as-is (the request was for something *in
  addition to* the side marker, not a replacement).
- The `IntersectionObserver` scroll-spy logic driving `setActive`.
- All page content/structure in `index.astro`, `detalhe-tecnico.astro` — no section IDs,
  ordering, or markup changes.

## Validation for the coding task

- `npm run build` succeeds.
- Visual check on `index.astro` and `detalhe-tecnico.astro`: each section fills at least one
  viewport; `capacidades` (taller, 4-tab content) is not clipped.
- Corner arrows are visibly larger/higher-contrast; existing disabled-at-boundary behavior
  still works; side dot markers unaffected.
- `npm run lint` passes.
- `instalacao.astro` renders unchanged (out of scope for both requests).
