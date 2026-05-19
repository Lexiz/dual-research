---
spec: 0095
title: M3 tabs + top app bar + chrome compaction (run-list 3→2 headers, top-bar layout when viewing a run)
label: bug
version-bump: PATCH
status: proposed
target-version: 0.72.4
created: 2026-05-19
pr: ""
---

# Spec 0095 — Tabs, top app bar, chrome compaction

> Ship bucket: **Primitives**
> Depends on: **0092, 0093**
> Complexity: **M**
> Targeted version bump: **PATCH** (bug-fix label resolves Issues 6 and 17)

## 1. Goal

Replace the existing run-list three-header strip with the M3
two-header layout (Issue 6) and clean up the run-detail top bar
(Issue 17 — remove the misplaced back button, add a vertical
divider, baseline-align the version chip and How-It-Works button).
Add the M3 primary-tabs and segmented-pill tab primitives so the
critique + timeline panes (later specs) have a single, canonical
tab implementation.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the M3
  primary-tabs block: `.md-tabs` + `.md-tab` + `.md-tab[aria-selected="true"]`
  with the 3 dp underline indicator per
  [v2-m3.css:573-597](docs/design-system-v2/assets/styles/v2-m3.css);
  the top app bar `.md-appbar` + `.md-appbar__title` +
  `.md-appbar__spacer` per
  [v2-m3.css:498-508](docs/design-system-v2/assets/styles/v2-m3.css);
  the segmented-pill `.tab-group-solid` + `.tab-solid` +
  `.tab-solid.is-active` (used by critique-pane Bar 2 in Spec
  0098) per
  [v2-m3-page.css:766-782](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the `.phase-tab` / `.kind-tab` from
  [v2-m3-page.css:681-763](docs/design-system-v2/assets/styles/v2-m3-page.css)
  (used by the critique pane and timeline tabs in 0098 / 0099 —
  defined here so later specs only have to compose, not author);
  the `.fgroup` / `.fgroup .ft` segmented-pill family from
  [v2-m3-page.css:1635-1651](docs/design-system-v2/assets/styles/v2-m3-page.css)
  (used in the critique pane filters).
- `src/dual_research/ui/static/run-list.jsx` — rewrite the
  three-header strip per Issue 6. Concretely (in render-tree
  order, top to bottom):
  - **Header 1** (was header 1 — "All runs / Compare / Search"
    buttons). Keep as the M3 top app bar carrying the brand mark
    + section title + right-cluster action buttons. Replace the
    hand-rolled three-button cluster with the M3 segmented control
    + the chip cluster from header 2 (`3 runs`, `$20.30 spent`,
    `live` indicator) moved to the right side of this bar,
    aligned with the search box.
  - **Header 2** (was header 2 — "dual-research / runs / 3 runs /
    $20.30 spent"): **delete** the brand-logo + "dual search" /
    "dual-research" text + "runs" empty word. **Move** the
    `3 runs` and `$20.30 spent` chips up to header 1's right
    side. **Move** the filter-tab strip (was header 3) up into
    the now-empty space, left-aligned. Net effect: header 2
    becomes the filter-tab row; the old header 3 disappears
    entirely.
  - **Header 3** (was header 3 — filter tabs): **delete**.
  After this rewrite, the run-list page has **two header bars**:
  `[brand + title | spacer | chips + search]` on top and
  `[all · running · converged · drift · errored · completed]`
  underneath.
- `src/dual_research/ui/static/app.jsx` — refactor the
  `RightCluster` component (line 266) for Issue 17:
  - **Remove** the `ActiveRunChip` rendering on the
    `route.view === 'detail'` path (line 271-273). The
    back-button-between-version-and-how-it-works the product
    owner flagged was this chip; deleting it is the fix. The
    user navigates back via the brand mark / left rail / browser
    back gesture instead.
  - **Insert** a vertical 20 dp divider (`<span class="vbar">`
    using the existing `.vbar` style from
    [v2-m3-page.css:679](docs/design-system-v2/assets/styles/v2-m3-page.css))
    between `AppVersionChip` and the `<Tab>` "How it works"
    button.
  - **Vertical-align** the version chip and the How-It-Works
    button to the 40 dp app-bar baseline. Replace the inline
    style on `AppVersionChip` so it reports a fixed `height:
    40px` and reads `align-items: center`. Replace the `<Tab>`
    component with a `<button class="md-btn md-btn--text
    md-btn--sm">` so its height matches via the atom contract.
    Both render at the same vertical center.
- `src/dual_research/ui/static/shared.jsx` — refactor `Tab` and
  `TabGroup` primitives to emit M3 markup. `Tab` accepts a
  `variant` prop (default `primary`; values: `primary`, `solid`,
  `kind`, `phase`, `chrome`). `primary` emits `<button
  class="md-tab" aria-selected="…">`; `solid` emits `<button
  class="tab-solid is-active">` inside `<div class="tab-group-solid">`;
  `kind` emits `.kind-tab`; `phase` emits `.phase-tab`; `chrome`
  emits a `.md-btn--text` button for the top app-bar use case.
  `TabGroup` wraps with the correct container class per variant.
- `pyproject.toml` — `0.72.3` → `0.72.4`.

## 3. Material 3 anatomy

- `#tabs` — primary tabs with full underline indicator + the
  three pill-style segmented tab variants. Top app bar
  (`md-appbar`) sticky at the top of every page.
- `#atoms` — segmented controls + buttons (read from Spec 0093).
- `#shape` — the 20 dp vertical divider (Issue 17) sits on the
  M3 4 dp grid (20 = 4 × 5).

Class-name contract:

```
.md-appbar, .md-appbar__title, .md-appbar__spacer
.md-tabs, .md-tab, .md-tab[aria-selected="true"]
.tab-group-solid, .tab-solid, .tab-solid.is-active, .tab-solid .dot
.phase-tabs, .phase-tab, .phase-tab.is-active, .phase-tab .pcode, .phase-tab .pname, .phase-tab .sigma
.kind-tabs, .kind-tab, .kind-tab.is-active, .kind-tab.is-zero, .kind-tab .ct, .kind-tab .ct.is-{info,warn,err}
.fgroup, .fgroup .ft, .fgroup .ft.is-active, .fgroup .ft .dot
.vbar
```

## 4. Notion issues addressed

1. **Issue 6 — Three headers in the run-detail strip should be
   reduced to two.** Source:
   `docs/design-system-v2/notion-issues/screenshots/06-three-headers.png`.
   The screenshot shows three stacked horizontal rows on the
   run-list page (top-bar with three buttons, second with brand
   + counts, third with filter chips). Resolution per § 2 above:
   delete the brand-logo-and-text from the second row, move the
   filter strip up into row 2, delete the now-empty row 3. Verify
   visually that the run-list page renders exactly two header
   bars after the change.

2. **Issue 17 — Top-bar layout when viewing an individual run.**
   Source: `docs/design-system-v2/notion-issues/screenshots/17-topbar-layout.png`.
   The screenshot shows `[connected] [v0.69.12] [back-arrow]
   [How it works] [theme-toggle] [avatar]` with the back-arrow
   (`←`) misplaced between the version chip and the How-It-Works
   button. Resolution per § 2 `RightCluster` refactor: delete
   that back-arrow chip entirely; insert a 20 dp vertical
   divider; baseline-align the version chip and How-It-Works at
   the 40 dp app-bar centre.

## 5. Acceptance criteria

- [ ] Issue 6: run-list page renders exactly two header bars at
      every breakpoint. The first is the top app bar; the second
      is the filter-tab strip. No third "dual-research · runs"
      row.
- [ ] Issue 6: the `3 runs` and `$20.30 spent` chips, plus the
      search input, render on the right side of the top app bar,
      vertically centered, baseline-aligned with the brand
      mark.
- [ ] Issue 17: navigating to `#/runs/<id>` and inspecting the
      app bar right cluster shows: `[connected] [v0.72.x]
      [vbar 20dp] [How it works button] [vbar] [theme-toggle]
      [avatar]`. No `←` back-arrow chip is present.
- [ ] Issue 17: the version chip (40 dp tall) and the How-It-Works
      button (40 dp tall via `.md-btn`) are baseline-aligned. No
      visible vertical jump.
- [ ] The vertical divider between the version chip and the
      How-It-Works button is exactly 20 dp tall (the chip
      height minus the M3 inset rule).
- [ ] M3 primary tabs render in any pane that uses them (verify
      via a quick stub in `design-language.jsx` or by waiting for
      Spec 0098/0099 to consume them).
- [ ] `Tab` primitive in `chrome` variant matches the 40 dp app-
      bar baseline; in `primary` variant matches the 48 dp tabs-
      row baseline.

## 6. Visual verification matrix

- `2200×1300 dark` — route `#/runs` (Issue 6 fix) AND
  `#/runs/<latest>` (Issue 17 fix). Both required.
- `2200×1300 light` — same.
- `1400×900 dark` — same two routes. Verify the run-list two-
  bar layout still fits without wrapping the search input below
  the chip cluster.
- `1400×900 light` — same.
- `820×1180 dark` — same routes; at this width the brand mark +
  chip cluster on top bar collapses into a hamburger-style
  overflow menu (M3 standard); the filter-tab row stays full
  width.
- `820×1180 light` — same.

All six required because Issue 6 + Issue 17 changes the chrome
layout, which is the highest-leverage regression surface.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database (`parseQId` for any
      q-id rendered in the chrome — N/A here, but verify the
      ActiveRunChip removal didn't break the run-id rendering on
      the run-list page).
- [ ] No emoji as icons.
- [ ] No off-grid spacing — chip heights 28 dp, button heights
      40 dp, divider 20 dp.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides where token roles cover the case.
- [ ] Reduced-motion contract preserved (tab indicator slide
      transition reads `--md-easing-emphasized-decel` at
      `--md-dur-medium-1`, killed under `reduce`).
- [ ] Focus ring visible on every tab + every right-cluster
      button.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0094-m3-cards-agentstrip-badges-hover-elevation.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The chrome compaction is layout-only. The
`AppVersionChip` reads `useAppMeta()` which is already exposed by
the live-data hook; no backend shape change.

## 11. CSS class anchor list

```
.md-appbar, .md-appbar__title, .md-appbar__spacer       → #tabs (top app bar)
.md-tabs, .md-tab                                       → #tabs (M3 primary tabs)
.tab-group-solid, .tab-solid                            → #tabs (segmented pill)
.phase-tabs, .phase-tab + variants                      → #critique (phase tabs in Bar 1)
.kind-tabs, .kind-tab + variants                        → #critique (kind tabs in Bar 2)
.fgroup, .fgroup .ft                                    → #critique (filter segmented)
.vbar                                                   → #tabs (top-bar vertical divider — Issue 17)
```
