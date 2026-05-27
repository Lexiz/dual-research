---
spec: 0104
title: Loading + States + A11y + Light + Responsive verification sweep (cross-cutting polish + verification of all earlier specs in both themes and three breakpoints)
label: test
version-bump: PATCH
status: proposed
target-version: 0.76.1
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0104 — Loading, States, A11y, Light, Responsive sweep

> Ship bucket: **Polish**
> Depends on: **0092, 0093, 0094, 0095, 0096, 0097, 0098, 0099, 0100, 0101, 0102, 0103**
> Complexity: **S**
> Targeted version bump: **PATCH** (test label — polish + cross-cutting verification, no new surface)

## 1. Goal

The final sweep. Two parts:
1. **Polish surfaces that weren't owned by any prior spec** —
   skeleton loaders, the six run-states gallery, the a11y
   acceptance bar, the light-mode preview, and the
   responsiveness rule documentation.
2. **Verification harness** — re-capture every Notion-issue
   resolution screenshot across both themes × three breakpoints
   to prove the 13-spec rebuild lands cleanly without
   regression. If anything is off, file a follow-up spec; do not
   silently patch.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the
  remaining design-system blocks:
  - **Loading**: `.skel` + `@keyframes md-shimmer` per
    [v2-m3-page.css:323-333](docs/design-system-v2/assets/styles/v2-m3-page.css);
    `.load-card` per
    [v2-m3-page.css:336](docs/design-system-v2/assets/styles/v2-m3-page.css).
    The shimmer reads `--md-dur-medium-4` (1.4 s) linear; never
    a spinner.
  - **States gallery** (design-language route only): `.states-
    grid` + `.state-card` + `.state-card .name` + `.state-card
    .desc` per
    [v2-m3-page.css:438-446](docs/design-system-v2/assets/styles/v2-m3-page.css).
  - **A11y row** (design-language route only): `.a11y-row` +
    `.a11y-row .name` + `.a11y-row .desc` per
    [v2-m3-page.css:449-455](docs/design-system-v2/assets/styles/v2-m3-page.css).
  - **Light frame** (design-language route only): `.lm-frame` +
    `.lm-frame__half` + `.lm-frame__half--{dark,light}` per
    [v2-m3-page.css:486-497](docs/design-system-v2/assets/styles/v2-m3-page.css).
  - **Responsive cards** (design-language route only):
    `.resp-grid` + `.resp-card` + `.resp-card .lbl` per
    [v2-m3-page.css:511-517](docs/design-system-v2/assets/styles/v2-m3-page.css).
- `src/dual_research/ui/static/shared.jsx` — refactor
  `LoadingState` (around line ~end of file) so the skeleton
  pattern reads from `.skel` and the shimmer reads from
  `@keyframes md-shimmer`. Replace any remaining
  `<div className="dr-spinner">` callsites with the skeleton
  pattern unless the spec explicitly calls for an inline spinner
  (search the repo for `dr-spinner` to enumerate). Per the
  design-system rule (`#loading`), never use a spinner — the
  eye registers the page shape immediately, then content fills
  in.
- `src/dual_research/ui/static/run-list.jsx` — replace the
  loading-state placeholder (currently the `LoadingState` panel)
  with a `.skel`-driven row skeleton matching the canonical
  pattern at
  [Design System v2.html#loading](docs/design-system-v2/assets/Design%20System%20v2.html)
  lines 2942-2974.
- `src/dual_research/ui/static/design-language.jsx` — append
  three documentation sections that render in the design-
  language route:
  - **States gallery** — a grid showing all six
    `<StatusBadge status="…">` chips with name + one-line
    description. Mirror
    [Design System v2.html#states](docs/design-system-v2/assets/Design%20System%20v2.html).
  - **A11y row** — five `.a11y-row` entries (focus ring,
    hit-area, contrast, reduced motion, semantic landmarks,
    skip link) per
    [Design System v2.html#a11y](docs/design-system-v2/assets/Design%20System%20v2.html)
    lines 3030-3053.
  - **Responsive cards** — four `.resp-card` blocks listing
    the rules per breakpoint bucket (≥1500 px, <1500 px,
    <900 px, rules of thumb) per
    [Design System v2.html#responsive](docs/design-system-v2/assets/Design%20System%20v2.html)
    lines 3101-3147.
- `src/dual_research/ui/static/app.jsx` — add a global skip
  link as the first element inside the app root: `<a
  className="skip-link" href="#main">Skip to main content</a>`.
  Style in `components.css`: visually hidden by default, visible
  on focus, jumps past the rail into `#main`. The main column
  receives the matching `id="main"` on its root div.
- `src/dual_research/ui/static/base.css` — verify (do not
  re-add) the `prefers-reduced-motion: reduce` global rule from
  Spec 0092 is present and unaltered. The polish spec re-asserts
  the contract as a checklist item; no CSS changes needed if
  Spec 0092 landed clean.
- `pyproject.toml` — `0.76.0` → `0.76.1`.

## 3. Material 3 anatomy

- `#loading` — skeleton loaders, two-stop shimmer at
  `--md-dur-medium-4` (1.4 s) linear. **Never a spinner.**
- `#states` — six canonical states (running · converged · drift
  · errored · idle · queued) with consistent colour contracts
  across status pill, timeline card outline, run-row left
  rule.
- `#a11y` — focus ring 3 px tertiary + 2 px offset; hit-area
  ≥ 48 × 48 dp on touch targets; reduced-motion killed by the
  global rule; semantic landmarks (`<header>`, `<aside aria-
  label>`, `<main>`, `<section id>`).
- `#light` — cream surfaces, deeper ink, slightly higher tint
  percentages because pastels need more saturation to show
  through cream.
- `#responsive` — three buckets (≥1500 px, <1500 px, <900 px);
  rules per bucket already covered in Spec 0092's foundation.
  This spec verifies them across every component.

Class-name contract:

```
.skel                              → #loading (skeleton)
@keyframes md-shimmer              → #loading (shimmer animation)
.load-card                         → #loading (skeleton container)

.skip-link                         → #a11y (visually-hidden skip link)

.states-grid, .state-card          → #states (design-language route)
.a11y-row                          → #a11y (design-language route)
.lm-frame, .lm-frame__half         → #light (design-language route)
.resp-grid, .resp-card             → #responsive (design-language route)
```

## 4. Notion issues addressed

This spec verifies the resolution of every prior Notion issue
(1-17) across two themes × three breakpoints. No new issue
introduced.

Verification list (each item maps to one acceptance criterion in
§ 5):

- Issue 1 (badge heights) — Spec 0094, verify at 2200×1300,
  1400×900, 820×1180 in both themes.
- Issue 2 (critique structure) — Spec 0098, same breakpoints.
- Issue 3 (phase headers + hover) — Spec 0094 (hover) + Spec
  0098 (header sizing), same breakpoints.
- Issue 4 (OK badges) — Spec 0093, same breakpoints.
- Issue 5 (phase indicators anchoring) — Spec 0099, the three
  scenarios + same breakpoints.
- Issue 6 (3 → 2 headers) — Spec 0095, same breakpoints.
- Issues 7, 8, 9, 10 (unified item-card family) — Spec 0097,
  same breakpoints.
- Issue 11 (double divider) — Spec 0099, same breakpoints.
- Issues 12, 13, 14, 15 (consumption rework) — Spec 0100, same
  breakpoints.
- Issue 16 (REPAIR explainer) — Spec 0099, same breakpoints.
- Issue 17 (top-bar layout) — Spec 0095, same breakpoints.

## 5. Acceptance criteria

- [ ] **Loading.** The run-list and run-detail loading state
      renders skeleton blocks with the two-stop shimmer at
      1.4 s linear. No `<div class="dr-spinner">` remains in
      any of the listed surfaces.
- [ ] **States gallery.** The design-language route renders
      all six state cards with consistent visual contract.
- [ ] **A11y — focus ring.** Every interactive primitive
      shows a 3 px tertiary focus ring with 2 px offset on
      `:focus-visible`. Verified by tabbing through the
      run-list, run-detail header, critique pane, consumption
      card, and tour callout buttons.
- [ ] **A11y — hit-area.** Every touch target is ≥ 48 × 48 dp
      in computed style (visual size ≥ 40 dp + 4 dp hidden
      padding ring on icon buttons).
- [ ] **A11y — contrast.** Run the page through axe-core or a
      similar contrast checker; verify all on-surface text
      hits AA at body sizes and AAA at headline+ sizes in both
      themes.
- [ ] **A11y — reduced motion.** Set DevTools
      `prefers-reduced-motion: reduce`; verify every transition
      and animation halts. The state-layer overlay,
      hover-elevation transition, chevron rotation, tour
      spotlight slide, and shimmer all freeze.
- [ ] **A11y — semantic landmarks.** Verify `<header>`,
      `<aside aria-label>`, `<main>`, and `<section id>` are
      present in the app shell. The skip link jumps to `#main`
      and is focusable as the first tab stop.
- [ ] **Light mode.** Every component the prior 12 specs touch
      renders correctly under `body.light`. Differential
      screenshot diff vs dark mode shows only the surface /
      ink palette swap, never per-component layout differences.
- [ ] **Responsive — three breakpoints.** Capture each of the
      17 Notion-issue resolutions at `≥1500 px`, `<1500 px`,
      `<900 px` and verify the fix holds at every width. File
      a follow-up spec for any breakpoint that breaks — do not
      silently patch.
- [ ] **Issue 1 — across all 6 viewports.** Both ModelBadges
      same height.
- [ ] **Issue 2 — across all 6 viewports.** Two-bar critique
      header, three states, status-grouped sections.
- [ ] **Issue 3 — across all 6 viewports.** Phase headers
      visibly taller than card headers; hover lifts cards but
      not headers.
- [ ] **Issue 4 — across all 6 viewports.** All OK badges
      render with the single canonical style.
- [ ] **Issue 5 — three scenarios × 6 viewports.** Markers
      anchored to visible phase headers; no rogue markers.
- [ ] **Issue 6 — across all 6 viewports.** Run-list shows
      exactly two header bars.
- [ ] **Issue 7 — across all 6 viewports.** Question card has
      no duplicate question text in the header.
- [ ] **Issue 8 — across all 6 viewports.** Disagreement card
      has no duplicate resolved badge at the top.
- [ ] **Issue 9 — across all 6 viewports.** Issue card has no
      cryptic `C-1`, no "flagged by · first seen · last seen",
      and no duplicate quote.
- [ ] **Issue 10 — across all 6 viewports.** Comment card
      follows the unified Issue-9 anatomy.
- [ ] **Issue 11 — across all 6 viewports.** One dashed
      divider between an expanded turn row and its body.
- [ ] **Issue 12 — across all 6 viewports.** Collapsed
      consumption card has three rows; no cost line.
- [ ] **Issue 13 — across all 6 viewports.** Unfolded
      consumption card has sub-rows + totals block + reuse
      marker + striped overlay.
- [ ] **Issue 14 — across all 6 viewports.** Consumption
      cards same width across P0..P4; round label above card.
- [ ] **Issue 15 — across all 6 viewports.** Legend sticky
      to the pane bottom; cards scroll under it.
- [ ] **Issue 16 — across all 6 viewports.** REPAIR row
      shows the inline chip + explainer body + 0-token chips.
- [ ] **Issue 17 — across all 6 viewports.** Top-bar shows
      `[connected] [version] [vbar] [How it works] [vbar]
      [theme] [avatar]` with no back-arrow chip and baseline
      alignment.

## 6. Visual verification matrix

This spec's whole purpose is verification. Capture **every
breakpoint × every theme** for every prior spec's fix:

- `2200×1300 dark` and `2200×1300 light` — primary diff target.
- `1400×900 dark` and `1400×900 light` — laptop bucket.
- `820×1180 dark` and `820×1180 light` — single-column.

Total expected screenshot count: ~6 viewports × ~13 surfaces ×
2 themes = on the order of 156 captures. Bundle into a single
PR comment as a grid (one row per surface, columns by viewport
× theme). Anything that doesn't match the expected anatomy gets
a follow-up spec, not a silent patch.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database.
- [ ] No emoji as icons.
- [ ] No off-grid spacing.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides where token roles cover the case.
- [ ] **Reduced-motion contract preserved** — this is the
      most-cited anti-pattern in the design system; the polish
      spec is where it's verified globally. Set
      `prefers-reduced-motion: reduce` and tab through the
      whole app; nothing animates.
- [ ] Focus ring visible on every focusable in every prior-
      spec surface. No `outline: none` overrides remain.
- [ ] **Polish anti-pattern:** the verification list is a
      checklist, not a debug session. If any item fails,
      branch into a follow-up spec rather than amending this
      one.
- [ ] **Polish anti-pattern:** no spinner remains as a primary
      loading affordance.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0103-onboarding-tour-overlay-progresssegs.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** This spec is verification + cross-cutting polish only.
No data-shape concerns; nothing to degrade gracefully against.

## 11. CSS class anchor list

```
.skel                                    → #loading (skeleton block)
@keyframes md-shimmer                    → #loading (shimmer animation)
.load-card                               → #loading (skeleton container)

.skip-link                               → #a11y (visually-hidden skip link)

.states-grid, .state-card                → #states (design-language gallery)
.state-card .name, .desc                 → #states (anatomy)

.a11y-row, .a11y-row .name, .desc        → #a11y (design-language list)

.lm-frame, .lm-frame__half               → #light (design-language preview)
.lm-frame__half--{dark,light}            → #light (paired panels)

.resp-grid, .resp-card                   → #responsive (design-language cards)
.resp-card .lbl                          → #responsive (small uppercase label)

(verification of all prior anchors: #identity, #principles, #palette, #type,
 #icons, #fmt, #shape, #elevation, #system, #atoms, #cards, #tabs, #critique,
 #thread, #consumption, #input, #timeline, #modal, #tour, #how, #admin,
 #changelog — all 27 anchors must render correctly after this spec.)
```
