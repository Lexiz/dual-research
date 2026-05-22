---
kind: dev
spec: "0167"
slug: critique-pane-bar2-chrome-and-bar1-drift-chip
title: Critique pane — bar2 segmented controls + bar1 drift chip + phase-tab + kind-cluster DS catch-up
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
queue_position: 3
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T17:08:41Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: critique-iteration-2026-05-22
promoted_from_draft: "004"
---

# Spec 0167 — Critique pane bar2 segmented controls + bar1 drift chip + DS catch-up

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — visible chrome changes on the critique pane header (bar1 + bar2) on every run-detail page. No data shape changes.

This is part 1 of the critique-pane refresh. Part 2 (spec 0168) handles the item-card itself.

---

## 1. Context

The critique pane (`.crit2` on the right column of `.rdvc__split`) has two header rows:

- **Bar 1** — phase tabs (P0 / P2 / P4 / Σ) on the left, run-wide totals (`.crit-totals`) on the right.
- **Bar 2** — kind cluster (Q / D / I / C / All) on the left, agent + status filter chips on the right, separated by `.crit-filter-spacer` dividers.

Five gaps in current state:

1. **Bar 2 right cluster is a flat row of plain chips with dividers.** Live renders agent (Claude / GPT) and status (Open / Resolved / Drift) as individual `<button class="chip tone-neutral no-dot">` chips separated by `<span class="crit-filter-spacer">` divider elements. The design-system reference at `design-system/SPEC.md` §4.1 + `design-system/assets/Design System v2.html` §12 documents these as `.tab-group-solid` segmented-control pills with `.tab-solid` options, an explicit "All" option per segment, and a lifted-tile active state (`var(--md-surface)` background + `--md-elev-1`). Live diverges.
2. **No bar1 drift chip.** Bar 1 has no run-wide drift indicator. The Drift status filter chip in bar 2 carries filter intent but no top-line visible-from-the-top signal exists. `design-system/SPEC.md` §4.1 already documents a `.drift-chip` slot in `.bar1 > .right`.
3. **Drift chip in bar2 silently drops count when count = 0.** The `.chip-value` span that surfaces the per-filter count is conditionally rendered. Open shows `(0)`, Resolved shows `(13)`, but Drift skips the span entirely when count is 0. The chip reads "Drift" with no count rather than "Drift (0)".
4. **Phase tabs disagree between live and DS.** Live renders P0 / P2 / P4 / Σ. `design-system/assets/Design System v2.html` §12 + `design-system/SPEC.md` §4.1 document only P2 / P4 / Σ. P0 Brief was added later; the DS reference was never updated.
5. **Kind-cluster order disagrees.** Live renders `Q / D / I / C / All`. DS / SPEC: `All / I / C / Q / D`. The live order is the locked target (matches the timeline `.tl-phase__chips` order); DS / SPEC must align.

All five gaps ship together in this MINOR release.

## 2. Proposed change

### 2.1 Bar 2 — segmented-control pills for agent + status

**Now.** Right cluster of `.bar2.crit-filter-row` is a flex row of plain `.chip.tone-neutral.no-dot` chips. Markup in `src/dual_research/ui/static/run-detail.jsx` (search for `crit-filter-row` or `crit-filter-spacer` — the bar2 render lives near the critique-pane render section).

**After.** Two `<div class="tab-group-solid">` segmented-control containers per `design-system/assets/Design System v2.html` §12 state-A markup. Each pill contains `.tab-solid` button options:

- **Agent segment.** `<div class="tab-group-solid" data-group="agent">` containing:
  - `<button class="tab-solid">All <span class="chip-value">(13)</span></button>`
  - `<button class="tab-solid">` Claude sunburst in sable square + `<span class="chip-label">Claude</span><span class="chip-value">(6)</span></button>` (use the existing brand-mark SVG cloned from the timeline identity chip)
  - `<button class="tab-solid">` OpenAI rosette in sage square + `<span class="chip-label">GPT</span><span class="chip-value">(7)</span></button>`
- **Status segment.** `<div class="tab-group-solid" data-group="status">` containing:
  - `<button class="tab-solid">All <span class="chip-value">(13)</span></button>`
  - `<button class="tab-solid">Open <span class="chip-value">(0)</span></button>`
  - `<button class="tab-solid">Resolved <span class="chip-value">(13)</span></button>`
  - `<button class="tab-solid">Drift <span class="chip-value">(0)</span></button>`

The agent segment uses live brand-icon SVGs (the same Claude sunburst inside a `--p-sable` 12×12 square and the OpenAI rosette inside a `--p-sage` 12×12 square that the timeline turn-card identity chip uses — cloned via shared helper from `src/dual_research/ui/static/shared.jsx`).

The explicit "All" option in each segment is the canonical "show all" reset. Clicking an already-active option in the agent or status segment deselects it (i.e. clicking the active "Claude" button while it's selected reverts to "All"). The implicit "no filter = show all" remains the data model — "All" is a click target, not a separate state.

**CSS** (lands in both `design-system/assets/styles/composed-components.css` and `src/dual_research/ui/static/components.css`):

```css
.crit2 .bar2 .tab-group-solid {
  display: inline-flex;
  background: var(--md-surface-container-high);
  border-radius: var(--md-shape-full);
  padding: 4px;
  gap: 2px;
  align-items: center;
}
.crit2 .bar2 .tab-group-solid .tab-solid {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  background: transparent;
  border: 0;
  border-radius: var(--md-shape-full);
  font: var(--md-w-medium) 11px/1 var(--md-font-plain);
  color: var(--md-on-surface-variant);
  cursor: pointer;
  transition: background var(--md-dur-short-3) var(--md-easing-standard),
              color      var(--md-dur-short-3) var(--md-easing-standard),
              box-shadow var(--md-dur-short-3) var(--md-easing-standard);
}
.crit2 .bar2 .tab-group-solid .tab-solid[data-active="true"] {
  background: var(--md-surface);
  color: var(--md-on-surface);
  box-shadow: var(--md-elev-1);
}
.crit2 .bar2 .tab-group-solid .tab-solid .chip-value {
  font: var(--md-w-regular) 10.5px/1 var(--md-font-data);
  color: currentColor;
  opacity: 0.6;
  margin-left: 4px;
  background: transparent;
  padding: 0;
  min-width: 0;
}
.crit2 .bar2 .tab-group-solid .tab-solid[data-active="true"] .chip-value {
  opacity: 0.75;
}
.crit2 .bar2 .tab-group-solid .tab-solid .chip-value::before { content: '('; }
.crit2 .bar2 .tab-group-solid .tab-solid .chip-value::after  { content: ')'; }

/* Bar 2 layout — kind cluster on left, segmented controls on right; never wraps */
.crit2 .bar2.crit-filter-row {
  gap: 8px;
  padding: 10px 12px;
  flex-wrap: nowrap;
  /* Single-row stability: nowrap also applies to the kind cluster and the
     two segmented controls so a long kind label or count never wraps onto a
     second line. The kind cluster scrolls horizontally inside its own slot
     before bar 2 itself wraps (see below). */
}
.crit2 .bar2.crit-filter-row > .kind-tabs {
  margin-right: auto;
  flex-wrap: nowrap;
  overflow-x: auto;        /* in case a kind label is unusually long */
  scrollbar-width: none;   /* hide cosmetic scrollbar in firefox */
}
.crit2 .bar2.crit-filter-row > .kind-tabs::-webkit-scrollbar { display: none; }

/* Bar 2 sticks to the top of the critique-pane body when the body scrolls.
   The pane body (`.crit2 > .crit2__body`) is the scroll container; bar 2
   uses position: sticky relative to that container so cards scroll under
   it while the chrome stays anchored. The z-index keeps bar 2 above the
   crit-group__hd sticky group headers (which use a lower z-index). */
.crit2 .bar2 {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--md-surface-container);
}

/* Narrow-mode count drop — labels stay, parens go */
@media (max-width: 1799px) {
  .crit2 .bar2 .tab-group-solid .tab-solid .chip-value { display: none; }
}
```

**Layout.** The right cluster carries agent THEN status (matching DS §12 state-A markup). The `.crit-filter-spacer` divider element is removed from JSX — the segmented-control pills provide visual grouping. Padding tightens from `16px` to `12px` horizontal, gap from `12` to `8` — at a 960 px critique-pane width (wide viewport), the total content row width fits in one row (918 px content in 936 px inner).

**Narrow-mode behaviour.** At viewports ≤ 1799 px, drop the `(N)` count parens from segmented controls (labels stay). The kind cluster reclaims ~100 px of horizontal room and bar 2 stays single-row. Kind chips already lose their text labels at narrow per an existing `@media` rule.

**Bar 2 stickiness (carried forward from the prototype iter 2.1 stabilisation work).** Bar 2 is `position: sticky` against the critique-pane body scroll container. When the user scrolls the phase view vertically, cards scroll under bar 2 while the agent / status / kind filters stay visible at the top. Background colour matches the pane (`--md-surface-container`) so cards visually pass under the chrome without bleed. `z-index: 5` keeps bar 2 above any `.crit-group__hd` sticky group headers (those use a lower z-index, defined in the existing live CSS for `.crit-group`). The DS reference in `Design System v2.html` §12 should be re-rendered with this sticky behaviour observable (a tall scrolling demo body beneath bar 2).

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — wrap the agent + status chip clusters in `<div class="tab-group-solid">` segments. Prepend explicit "All" `<button class="tab-solid">` to each. Drop `.crit-filter-spacer` elements. Add `<span class="chip-value">({N})</span>` to every option (including "All" + "Drift" when count = 0).
- `src/dual_research/ui/static/components.css` — add the `.tab-group-solid` + `.tab-solid` rules above.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §4.1 — codify the segmented-control composition and the lifted-tile active state.
- `design-system/assets/Design System v2.html` §12 — already documents the segmented control; verify the rendered example matches.

### 2.2 Drift chip count slot always rendered (drift 3.K)

**Now.** Status filter chips render the count via `.chip-value`. Open and Resolved always include the span even when count is 0. Drift skips the span entirely when count is 0 — the chip reads "Drift" instead of "Drift (0)". The chip width fluctuates when drift items appear/disappear during a run.

**After.** Always render the `.chip-value` span for every option in the status segment. When count is 0, the span content is `0` (which then renders as `(0)` via the `::before`/`::after` parens content). The chip layout stays stable.

The same rule applies to "All" — it always renders the run total, even at start of run (`(0)`).

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — remove the `count > 0` conditional around the `.chip-value` span rendering for the Drift option specifically.

### 2.3 Bar 1 drift chip — new slot in `.right`

**Now.** Bar 1 right cluster (`.bar1 > .right`) contains only `<span class="crit-totals">…</span>`. No top-line drift indicator.

**After.** Add a new `<span class="drift-chip" data-count={N}>` element to `.bar1 > .right` immediately after `.crit-totals`:

```html
<span class="drift-chip" data-count="3">
  <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
    <path d="M1,21h22L12,2L1,21z M13,18h-2v-2h2V18z M13,14h-2v-4h2V14z" fill="currentColor" />
  </svg>
  3 drift
</span>
```

**Styling** (lands in both DS + live CSS files):

```css
.crit2 .bar1 .drift-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: var(--md-shape-full);
  background: color-mix(in srgb, var(--p-err) 18%, transparent);
  color: var(--p-err);
  font: var(--md-w-medium) 11px/1 var(--md-font-plain);
  letter-spacing: 0.4px;
}
.crit2 .bar1 .drift-chip svg { width: 12px; height: 12px; }

/* Muted variant when count = 0 — slot stays present so chrome doesn't reflow */
.crit2 .bar1 .drift-chip[data-count="0"] {
  background: color-mix(in srgb, var(--md-on-surface) 6%, transparent);
  color: var(--md-on-surface-faint);
  opacity: 0.55;
}
```

The slot is always present (`data-count="0"` muted variant when count is 0) so the bar-1 chrome doesn't reflow if drift appears mid-run. The 28 px full-radius pill matches the `.crit-totals` chip geometry. The `⚠` icon (Material Icons "warning" triangle path) is inlined as SVG.

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — in the bar-1 render of `.crit2`, add `<DriftChip count={runTotals.drift} />` after `<crit-totals>`. The helper component is defined in `shared.jsx` or inline.
- `src/dual_research/ui/static/components.css` — add the `.drift-chip` rules.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §4.1 — already documents this slot; verify the muted-at-0 variant is captured.
- `design-system/assets/Design System v2.html` §12 — already renders the drift chip in state A; add a `data-count="0"` muted variant for visual reference.

### 2.4 Phase-tab DS catch-up — P0 Brief

**Now.** `design-system/assets/Design System v2.html` §12 (and `design-system/SPEC.md` §4.1) document phase tabs `P2 / P4 / Σ`. Live renders `P0 / P2 / P4 / Σ`. P0 Brief was added later; DS reference was never updated. No live change needed — only DS.

**After.** Add `P0 Brief` to each of the rendered states A/B/C in `design-system/assets/Design System v2.html` §12. Update `design-system/SPEC.md` §4.1 phase-tab description to enumerate four tabs.

**Files to change.**
- `design-system/SPEC.md` §4.1 — update the phase-tab description.
- `design-system/assets/Design System v2.html` §12 states A/B/C — add the `P0 Brief` tab.

### 2.5 Kind-cluster order — DS / SPEC align with live

**Now.** Live renders `Q / D / I / C` (with no "All" — see §2.6 below for the "All" removal). DS `.kind-tabs` markup in `design-system/assets/Design System v2.html` §12 and SPEC.md §4.1 enumerate `All / I / C / Q / D`. The live order matches the timeline `.tl-phase__chips` cluster — visual consistency across panes is the higher priority.

**After.** DS + SPEC align with live. The canonical order is `Q · D · I · C` (no leading "All" — see §2.6). The chip primitive remains `.chip` + `.cat-bubble` (shared with `.tl-phase__chips`). No `.kind-tab` flat-tab primitive — that pattern is dropped from DS.

**Files to change.**
- `design-system/SPEC.md` §4.1 + §9.6 — codify that critique bar-2 kind filters use the same `.chip` + `.cat-bubble` primitive as `.tl-phase__chips`. The letter-bubble carries kind identity (Q / D / I / C) across panes.
- `design-system/assets/Design System v2.html` §12 — replace any `.kind-tab` markup with the live `.chip[data-kind-filter]` markup. The chips render in the locked order Q · D · I · C.
- `design-system/assets/styles/v2-m3-page.css` (or `composed-components.css`, wherever the DS hosts the `.kind-tab` rules) — remove the `.kind-tab` selector block. The `.chip[data-kind-filter]` styling is already correct (inherits from the `.chip` primitive).

### 2.6 Kind cluster — drop the "All" chip

**Now.** Live renders five chips in the kind cluster: `Q · D · I · C · All`. The "All" chip is `.chip.tone-neutral`; the four category chips are `.chip.tone-info` / `.tone-warn` / `.tone-err` / `.tone-idle`. The "All" chip is a redundant reset — same convention as the agent + status segments was changed to in §2.1 (where "All" is now an explicit button option, but only inside the segmented control).

**After.** Drop the "All" chip from the kind cluster. The cluster is four chips: `Questions [N] · Disagreements [N] · Issues [N] · Comments [N]`. No active kind chip = "show all categories". Clicking an active kind chip deselects it.

The bar-1 `.crit-totals` (`13 introduced · 0 open · 13 resolved`) is the run-wide global; the kind cluster shows per-kind phase counts. No "All" reset is needed in the kind cluster — it's redundant with both the data model and the bar-1 totals.

**CSS** (the rule lives in both files):

```css
.crit2 .bar2 .kind-tabs .chip[data-kind-filter].tone-neutral { display: none; }
.crit2 .bar2 .kind-tabs { display: inline-flex; gap: 4px; align-items: center; flex-wrap: nowrap; }
```

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — in the kind-cluster render, drop the "All" chip rendering or guard it behind a feature flag that defaults to off.
- `src/dual_research/ui/static/components.css` — `.kind-tabs` flex group + the hide rule.
- `design-system/assets/styles/composed-components.css` — same.

## 3. UX / behaviour

After this spec lands:

- **Bar 1.** Phase tabs read `P0 · P2 · P4 · Σ`. Run-wide totals are on the right, followed by the new drift-chip slot. When the run has 0 drift items, the slot renders muted (`⚠ 0 drift` at ~55 % opacity) so the chrome doesn't reflow if drift appears mid-run. When the run has drift items, the slot renders at full err-color saturation (`⚠ 3 drift`).
- **Bar 2.** Kind cluster on the left as four chips (Q · D · I · C) — no "All" reset. Segmented-control pills on the right for agent (`[All (13)] [Claude (6)] [GPT (7)]`) and status (`[All (13)] [Open (0)] [Resolved (13)] [Drift (0)]`). Every option carries its phase-scoped count. Active option is the lifted tile (`var(--md-surface)` + `elev-1`). Clicking an active option deselects it.
- **Narrow mode (viewport ≤ 1799 px).** Bar 2 stays single-row. The `(N)` count parens drop from the segmented-control labels (labels stay). Kind chips lose their text labels per existing live `@media` rule.
- **DS reference reconciled.** `Design System v2.html` §12 now shows P0 Brief, the locked kind-cluster order, the muted drift-chip variant. `SPEC.md` §4.1 documents the bar-1 drift slot, the segmented-control pattern, and the kind-cluster primitive sharing with `.tl-phase__chips`.

Existing runs render identically except for the chrome changes — no schema migration, no data layer changes.

## 4. Data / schema deltas

None. The drift count consumed by the new chip is already present in the existing `runTotals` aggregate on the run-detail page. The agent/status filter state is unchanged; only the chip composition changes.

## 5. Out of scope

- **Item-card frame / head rebuild / expanded view / source attribution badges / affordances** — covered by spec 0168.
- **Σ Summary tab body, bar-1 totals reset bug, Σ inline-style cleanup** — these are separate concerns (drift 3.F, 3.G, 3.H in the critique iteration notes) and ship as their own spec(s) later. Out of scope here.
- **Resolved group title split into per-state groups** (drift 3.E) — separate concern; out of scope.
- **Kind-cluster ordering rule for the timeline pane** — already locked there; this spec only ensures the critique pane matches.

## 6. Design-system gate

Cited DS sections being updated:

- `design-system/SPEC.md` §4.1 — phase-tab P0 Brief, segmented-control pattern documentation, bar-1 drift-chip slot, kind-cluster primitive sharing.
- `design-system/SPEC.md` §9.6 — kind-cluster letter-bubble primitive (Q / D / I / C) shared between timeline and critique.

Files that MUST land in the same commit:

- `design-system/SPEC.md`
- `design-system/assets/styles/composed-components.css`
- `design-system/assets/styles/v2-m3-page.css` (if it hosts the `.kind-tab` rules being removed)
- `design-system/assets/Design System v2.html` (§12 rendered examples updated)
- `src/dual_research/ui/static/components.css`
- `src/dual_research/ui/static/run-detail.jsx`
- `src/dual_research/ui/static/shared.jsx` (DriftChip helper if extracted; otherwise inline in run-detail.jsx)
- `CHANGELOG.md`
- `pyproject.toml`
- `src/dual_research/__init__.py`

## 7. Test plan

- [ ] **Bar 2 segmented controls — render structure.** Open a run with critique items. `document.querySelectorAll('.crit2 .bar2 .tab-group-solid').length === 2`. The first has `data-group="agent"` and contains three `.tab-solid` buttons (All / Claude / GPT). The second has `data-group="status"` and contains four (All / Open / Resolved / Drift).
- [ ] **Bar 2 segmented controls — count slot always rendered.** Every `.tab-solid` button has a `.chip-value` child element. Drift's `.chip-value` contains text `0` even when there are no drift items.
- [ ] **Bar 2 segmented controls — active state.** Click the "Claude" option. It gets `data-active="true"`. Computed `background-color` resolves to `--md-surface`, computed `box-shadow` resolves to `--md-elev-1`. Click "Claude" again — `data-active` flips off and the All button becomes the implicit reset (no `data-active` set).
- [ ] **Bar 2 nowrap.** Resize the workshop iframe to 960 px wide (wide critique pane). All bar-2 content fits in one row — no wrap.
- [ ] **Bar 2 narrow-mode counts.** Resize to 640 px (narrow). `.chip-value` elements inside segmented controls have computed `display: none`. Labels remain visible.
- [ ] **Bar 2 sticky on body scroll.** Open a run with enough cards to overflow the critique-pane body. Scroll the pane vertically. `.crit2 .bar2` stays anchored at the top of the pane (`getBoundingClientRect().top` value relative to the pane is constant). Cards scroll under bar 2 with no visual bleed (bar 2 background matches the pane container token). The z-index keeps bar 2 above any `.crit-group__hd` sticky headers.
- [ ] **Bar 2 single-row at all widths.** At every supported critique-pane width (narrow ≤ 1799 px and wide), bar 2's `.bar2.crit-filter-row` does NOT wrap. The kind cluster's `.kind-tabs` has `flex-wrap: nowrap` and overflows horizontally inside its own slot before bar 2 itself wraps.
- [ ] **Bar 1 drift chip — non-zero.** Render a run with drift items. `.crit2 .bar1 .drift-chip` exists with `data-count="3"` (or whatever the actual count is). Computed `background-color` resolves to `color-mix(in srgb, var(--p-err) 18%, transparent)`, computed `color` resolves to `--p-err`.
- [ ] **Bar 1 drift chip — zero count muted.** Render a run with 0 drift items. The chip still renders with `data-count="0"`. Computed `opacity === 0.55`. Computed `color` resolves to `--md-on-surface-faint`. The slot occupies space — toggling drift count from 0 to 1 doesn't reflow the bar-1 right cluster (verified via measuring `.bar1 .right` width before / after).
- [ ] **Phase tabs — P0 in DS.** Open `design-system/assets/Design System v2.html` §12 in a browser. All three rendered states show four phase tabs: P0 Brief, P2, P4, Σ.
- [ ] **Kind cluster — no "All" chip.** `.crit2 .bar2 .kind-tabs .chip.tone-neutral[data-kind-filter]` is either absent from the DOM or has computed `display: none`. The cluster shows four chips (Q · D · I · C). Counts in `.chip-value` are accurate.
- [ ] **Kind cluster — order.** The four kind chips render in order Q · D · I · C in the DOM (`Array.from(document.querySelectorAll('.kind-tabs .chip')).map(c => c.querySelector('.cat-bubble').textContent)` returns `['Q', 'D', 'I', 'C']`).
- [ ] **DS catch-up — DS uses .chip primitive.** `design-system/assets/Design System v2.html` §12 markup does NOT contain `<button class="kind-tab">` elements. It uses `<button class="chip ...">` with `.cat-bubble` children.
- [ ] **Old-run safety.** Render `/runs/<earliest-archived-run>`. The new bar1 / bar2 chrome renders without console errors. Old runs without drift data render the muted drift chip (`data-count="0"`).
- [ ] **Tests pass.** `uv run pytest tests/ -q` exits 0.

## 8. Implementation steps (suggested order)

1. Update `design-system/SPEC.md` §4.1 + §9.6 first (text contract before code).
2. Update `design-system/assets/Design System v2.html` §12 — add P0 tab, reorder kind cluster, render the muted drift chip, document the `.tab-group-solid` segmented control.
3. Remove `.kind-tab` rules from `design-system/assets/styles/v2-m3-page.css` if present.
4. Add `.tab-group-solid` / `.tab-solid` / `.drift-chip` rules to `design-system/assets/styles/composed-components.css`.
5. Mirror to `src/dual_research/ui/static/components.css`.
6. Refactor `src/dual_research/ui/static/run-detail.jsx`:
   - Wrap agent + status chips in `.tab-group-solid` containers.
   - Drop `.crit-filter-spacer` elements.
   - Drop the kind-cluster "All" chip.
   - Add the drift-chip render in bar 1.
   - Backfill the drift `.chip-value` so count = 0 still renders `(0)`.
7. Run the test plan in full.
8. CHANGELOG entry under a new `## [X.Y.Z] — YYYY-MM-DD` section. Bump `pyproject.toml` + `src/dual_research/__init__.py` per MINOR.
