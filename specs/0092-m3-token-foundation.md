---
spec: 0092
title: Material 3 token & foundation layer (palette, type, shape, elevation, state, motion, density, fonts, icons, base)
label: refactoring
version-bump: PATCH
status: proposed
target-version: 0.72.1
created: 2026-05-19
pr: ""
---

# Spec 0092 — M3 token & foundation layer

> Ship bucket: **Foundation**
> Depends on: —
> Complexity: **M**
> Targeted version bump: **PATCH** (no user-visible feature; foundation only)

## 1. Goal

Lay down the complete Material 3 token layer so the rest of the
visual rebuild can read tokens instead of hex codes. After this
spec lands, **no component CSS changes are visible to the user** —
the page renders identically — but every subsequent spec (0093 …
0104) can read `--md-*` role tokens and the Roboto Flex / Roboto
Serif font pair, and can target the two new responsive breakpoints
(<1500 px and <900 px) and the comfortable/compact density toggle
without touching theme files.

This is the substrate. Nothing else in this rebuild works without
it.

## 2. Files touched

Group by file, one-line summary of what changes:

> **Rewrite note (Step 3 Rewrite, 2026-05-19):** the original draft
> said "replace" for the v1 token tree, body font, dark/light flip,
> and boot block — that contradicted § 1 Goal ("page renders
> identically") and acceptance § 5.9 ("v1 visual appearance
> preserved"). Reframed to **add alongside** v1 — the M3 layer
> becomes *available* but the rendered surface stays v1. Subsequent
> specs (0093…0104) swap components one by one.

- `src/dual_research/ui/static/tokens.css` — **append** the full
  M3 token set after the existing v1 tokens. The v1 `--bg-*` /
  `--fg-*` / `--border-*` / `--agent-*` / `--ok` / `--info` /
  `--warn` / `--err` / `--idle` definitions are preserved verbatim
  (981 references across `*.css` and `*.jsx` keep working). Add
  on top: colour roles (`--md-primary`, `--md-secondary`,
  `--md-tertiary`, `--md-error`, plus `-container` + `--md-on-*`
  pairs); surface tiers (`--md-surface`, `--md-surface-{dim,bright}`,
  `--md-surface-container-{lowest,low,_,high,highest}`); derived
  `--md-surface-1..5` via `color-mix` with surface tint; shape
  scale (`--md-shape-xs/sm/md/lg/xl/full`); 15-role M3 type scale;
  spacing scale (`--md-sp-0..20`); 6-level elevation; 4 state-
  layer opacities; M3 easings + 8 duration tokens; focus-ring +
  focus-offset. Mirror verbatim the values in
  [docs/design-system-v2/assets/styles/v2-m3.css](docs/design-system-v2/assets/styles/v2-m3.css)
  lines 7-174. Add the `--p-*` palette source vars (sable, sage,
  info, ok, warn, err, idle) at the top of the M3 block so role
  tokens reference them, not raw hex. The v1 dark/light flip stays
  in `tokens.css` `body.light` block; append a parallel
  `body.light` block that overrides the new `--md-*` role tokens
  per [v2-m3.css:200-245](docs/design-system-v2/assets/styles/v2-m3.css).
- `src/dual_research/ui/static/theme.css` — **append** `body.tint-
  secondary` for sage-on-GPT tinting per
  [v2-m3.css:177-180](docs/design-system-v2/assets/styles/v2-m3.css)
  and `body.compact` density override per
  [v2-m3.css:183-198](docs/design-system-v2/assets/styles/v2-m3.css).
  The existing legacy component rules (`.phase-step-line`,
  `.uppercase-label`, `.dr-ghost-block`, `.dr-section-brief-btn`,
  `.cap-bar`, `.bg-grid`) are **untouched** — they drain in
  subsequent specs.
- `src/dual_research/ui/static/base.css` — **append** the M3
  utilities after the existing v1 boot block. New rules:
  the 15 `.t-*` M3 role classes (`.t-display-l` … `.t-label-s`,
  `.t-data`), the `.muted` / `.faint` / `.subtle` colour helpers
  (only if no collision with existing classes), and a
  `prefers-reduced-motion: reduce` companion rule that kills
  motion via the M3-shaped `* { transition: none !important;
  animation: none !important; }`. The existing v1 `.t-display`,
  `.t-title`, `.t-h3`, `.t-body`, `.t-meta`, `.t-mono`, `.t-label`
  classes are **untouched** so components keep rendering as
  today. The existing `html, body { font-family: var(--sans); }`
  declaration stays — body font does NOT swap to Roboto Flex.
  Mirror the new utilities from
  [v2-m3.css:247-298](docs/design-system-v2/assets/styles/v2-m3.css).
- `src/dual_research/ui/static/index.html` — **add** the M3 font
  links (`Roboto+Flex:opsz,wght@8..144,100..1000`,
  `Roboto+Serif:opsz,wght@8..144,300..800`) and the Material
  Symbols Outlined stylesheet
  (`family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0`)
  alongside the existing `IBM+Plex+Sans` / `IBM+Plex+Serif`
  preconnect/link (both pairs load; rendered body font stays
  IBM Plex). Bump the cache-bust `?v=` from `0093` to `0094`
  (we're behind the previous bump in v1) on every existing
  `<link>` / `<script>` tag. **Do not** import the design-system
  bundle's HTML or CSS; this spec mirrors those tokens into the
  app's own files.
- `src/dual_research/ui/static/components.css` — add the
  `.ms` / `.ms-18` / `.ms-20` / `.ms-24` icon-sizing helpers so
  the Material Symbols Outlined ligatures render at the documented
  three sizes (18 dp inside chips, 20 dp inside buttons, 24 dp in
  chrome). Existing v1 component CSS in this file is **untouched**
  — subsequent specs replace it block by block. This spec only
  appends the `.ms` helpers and a single `.responsive-grid`
  utility class.
- `pyproject.toml` — bump `version = "0.72.0"` → `"0.72.1"`. Label
  is `refactoring` so the bump is PATCH.

Notably **not** touched in this spec: any `.jsx` file, any v1
component CSS, the v1 body font, any backend file.

## 3. Material 3 anatomy

Anchors implemented in this spec, with the canonical reference
file inlined as a pointer (not duplicated — the implementer reads
the design-system file directly for the verbatim values):

- `#identity` — agent-tint contract: sable on Claude routes,
  sage on GPT routes (flip via `body.tint-secondary`). See
  [Design System v2.html#identity](docs/design-system-v2/assets/Design%20System%20v2.html).
- `#principles` — read-only discipline (no spec adds buttons
  that mutate run state), comfortable density default, light mode
  is theme-agnostic.
- `#palette` — the seven palette source colours
  (`--p-sable`, `--p-sage`, `--p-info`, `--p-ok`, `--p-warn`,
  `--p-err`, `--p-idle`) plus the M3 role overlay (`--md-primary`
  = sable, `--md-secondary` = sage, `--md-tertiary` = info,
  `--md-error` = err). Verbatim hex values in
  [v2-m3.css:9-17](docs/design-system-v2/assets/styles/v2-m3.css).
- `#type` — M3 fifteen-role scale (display L/M/S, headline L/M/S,
  title L/M/S, body L/M/S, label L/M/S). Plain font Roboto Flex,
  brand font Roboto Serif (used for display / headline / serif
  italic quotes), data font Roboto Flex with `tnum, ss01` feature
  settings.
- `#icons` — Material Symbols Outlined at 18 dp inline, 20 dp in
  buttons, 24 dp in chrome. Outlined weight 400, optical-size 24.
  Agent brand marks (sable burst, sage rosette) **remain custom**
  — they are NOT swapped for Material Symbols.
- `#fmt` — one canonical representation per number. Token counts
  with en-US grouping (`42,718`), cost with 3 decimals
  (`$0.084`), duration `mm:ss` or `h:mm:ss`, run IDs lowercase
  with hex friendly dashes. `font-variant-numeric: tabular-nums`
  + `font-feature-settings: "tnum", "ss01"` baked into
  `.t-data`.
- `#shape` — six-step shape scale: xs 4 · sm 8 · **md 12
  (default)** · lg 16 · xl 28 · full 9999. Spacing on the M3 4 dp
  half-step grid (`--md-sp-0..20`).
- `#elevation` — six elevation levels (`--md-elev-0..5`); each
  level pairs a shadow recipe with a tonal-overlay surface
  (`--md-surface-1..5` mixed from `--md-surface-tint` at 5/8/11/12/14
  % opacity via `color-mix`).
- `#system` — colour roles, surface tiers, shape, spacing,
  motion, state-layer opacities are all expressed as `--md-*`
  tokens. Theme/tint/density toggles re-resolve the whole tree by
  flipping a body class; **no component CSS changes per theme.**

Exact CSS class anchors introduced (boot-block utilities only —
component CSS is later specs):

```
.t-display-l, .t-display-m, .t-display-s   → #type (display roles)
.t-headline-l, .t-headline-m, .t-headline-s → #type (headline roles)
.t-title-l, .t-title-m, .t-title-s          → #type (title roles)
.t-body-l, .t-body-m, .t-body-s             → #type (body roles)
.t-label-l, .t-label-m, .t-label-s          → #type (label roles)
.t-data                                     → #fmt (tabular numerics)
.muted, .faint, .subtle                     → #system (on-surface tones)
.ms, .ms-18, .ms-20, .ms-24                 → #icons (Material Symbols sizing)
```

## 4. Notion issues addressed

Implements design-system foundation only; no Notion issue. All 17
issues become addressable in their respective specs once this
spec lands, because each one reads tokens defined here.

## 5. Acceptance criteria

> **Rewrite note (Step 3 Rewrite, 2026-05-19):** original criterion
> 1 (body fontFamily contains "Roboto Flex" as the first declared
> family) contradicted § 1 Goal ("page renders identically"). The
> body font stays IBM Plex; Roboto Flex/Serif and Material Symbols
> are *loaded and available* for subsequent specs. Reworded so
> font availability is checked via the font face being present,
> not via body.fontFamily.

- [ ] Computed `getComputedStyle(document.body).getPropertyValue(
      '--md-font-plain')` resolves to a string containing
      `"Roboto Flex"`. Body's rendered `font-family` is unchanged
      (still resolves with `"IBM Plex Sans"` first). Subsequent
      specs flip individual components onto `--md-font-plain`.
- [ ] Computed `getComputedStyle(document.body).getPropertyValue(
      '--md-primary')` resolves to the sable hex (`#d4a574`) when
      `body.tint-secondary` is absent, and the sable hex is still
      readable (tint-secondary only flips
      `--md-surface-tint`, not `--md-primary`).
- [ ] Adding `body.light` flips `--md-surface` from the dark
      `#0d0f12` to the cream `#faf9f6` without any component CSS
      re-rendering — verify by toggling `document.body.classList`
      in DevTools.
- [ ] Adding `body.compact` flips `--md-pad-card` from `24px` to
      `16px` and `--md-row-h` from `56px` to `44px`.
- [ ] Viewport-driven `--md-rail-w` rule is **deferred** to a
      subsequent spec — this spec lays the token only (default
      280 px / compact 240 px); no `@media (max-width: 1499px)`
      override yet.
- [ ] The Material Symbols Outlined font loads (network panel
      shows the woff2 fetch and a 200 response). Rendering a
      literal `<span class="ms">check_circle</span>` in the
      DevTools console produces the glyph, not the literal
      string. (No `<span class="ms">` is added to live UI in
      this spec.)
- [ ] Reduced-motion contract preserved: setting
      `prefers-reduced-motion: reduce` in DevTools kills every
      CSS transition and animation in the page (existing
      `base.css` rule remains authoritative; the M3 companion
      rule reinforces it).
- [ ] Page reload preserves the v1 visual appearance of every
      existing component — this spec is invisible to the user.
      Verified via side-by-side screenshot diff of run-list and
      run-detail in both themes.

## 6. Visual verification matrix

The change is foundation only; verification is regression-only
(no new visual surface). Capture:

- `2200×1300 dark` (route `#/runs`)
- `2200×1300 light` (route `#/runs`)
- `1400×900 dark` (route `#/runs/<latest>`)
- `1400×900 light` (route `#/runs/<latest>`)

Skip the `820×1180` breakpoints for this spec because the boot
block doesn't change layout at <900 px — the responsive collapse
is done by `display: grid; grid-template-columns:` rules in
subsequent specs. Document the skip in the PR description with a
one-line rationale.

For each captured screenshot, diff visually against the same
viewport / route taken from `main` at the commit immediately
before this spec merges. The diff must be **zero pixels**
intentional change — the goal is foundation parity. Any
regression aborts the spec.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database (use `QuestionRef`
      decoding via `parseQId`) — N/A for foundation; relevant once
      cards land.
- [ ] No emoji as icons (Material Symbols Outlined only).
- [ ] No off-grid spacing (4 px / 8 px grid).
- [ ] No hex codes in component CSS (token roles only —
      `var(--md-*)`). Source palette hex values are allowed
      **only** inside `--p-*` definitions at the top of
      `tokens.css`.
- [ ] No per-theme overrides where token roles cover the case.
      `body.light` only redeclares `--md-*` role tokens, never
      component selectors.
- [ ] Reduced-motion contract preserved
      (`prefers-reduced-motion: reduce`) — verified by the global
      `* { transition: none !important; animation: none !important; }`
      rule in `base.css`.
- [ ] Focus ring visible on every focusable.

## 8. Handover read

> *First task on running this spec: read `docs/design-system-v2/README.md` end-to-end, then `handoffs/2026-05-19-data-integrity-arc-complete.md` end-to-end.*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** This spec changes only the static frontend token layer.
The backend exposes the same shapes after this spec lands. Degrade-
gracefully is not relevant — there's no data shape involved.

## 11. CSS class anchor list

```
:root  declarations             → #palette #type #shape #elevation #system (the M3 token set)
body.light                       → #light (theme flip)
body.compact                     → #responsive (density flip)
body.tint-secondary              → #identity (agent-tint flip)

.t-display-l / m / s             → #type (display roles)
.t-headline-l / m / s            → #type (headline roles)
.t-title-l / m / s               → #type (title roles)
.t-body-l / m / s                → #type (body roles)
.t-label-l / m / s               → #type (label roles)
.t-data                          → #fmt (tabular numerics)

.muted, .faint, .subtle          → #system (on-surface variants)

.ms                              → #icons (Material Symbols base)
.ms-18, .ms-20, .ms-24           → #icons (size variants)

@media (max-width: 1499px)       → #responsive (laptop bucket)
@media (max-width: 900px)        → #responsive (tablet bucket)
@media (prefers-reduced-motion: reduce) → #a11y (reduced motion contract)
```
