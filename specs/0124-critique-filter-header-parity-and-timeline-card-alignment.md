---
spec: 0124
title: Critique filter header height parity + responsive compaction + timeline card right-alignment
label: bug
version-bump: PATCH
status: in-flight
target-version: 1.5.2
created: 2026-05-20
pr: "https://github.com/Lexiz/dual-research/pull/135"
---

# Spec 0124 — Critique filter header height parity, responsive compaction, and timeline card right-alignment

> Ship bucket: **Frontend-only polish to the run-detail two-pane view (spec 0107 surface).**
> Depends on: **0107** (timeline + critique two-pane layout), **0119** (badge vocabulary), **0111** (critique filter row first introduced).
> Complexity: **S** — three narrow CSS / JSX changes to `run-detail.jsx` and `components.css`.
> Targeted version bump: **PATCH (1.5.1 → 1.5.2)** — visual fixes, no behavior or contract changes.

---

## 1. Context

Three visual defects on the run-detail screen, all in the two header bars that sit immediately under the run-detail chrome:

1. **Wide-screen height mismatch.** The left pane's "Conversation / Consumption" tab strip (`.tl__tabs`) is **55 px tall** (`min-height: 55px; padding: 10px 20px`). The right pane's critique filter row (`.crit-filter-row`) is **~45 px tall** (`padding: 10px 14px`, no `min-height`). Sitting side-by-side on a wide monitor, the two header bands no longer share a baseline — the critique filter looks visibly stunted next to the tabs band, and the seam between them is jagged. (See screenshot 1 — `bar2 crit-filter-row` on the right is ~10 px shorter than `tl__tabs` on the left.)

2. **Small-screen wrap-and-grow.** On laptop-width viewports (≲ 1500 px wide), the same `.crit-filter-row` has `flex-wrap: wrap` and ten labelled chips (`Questions n · Disagreements n · Issues n · Comments n · All n · Open n · Resolved n · Drift · Claude · GPT`). The chips wrap to a second row, which pushes the header to ~90 px tall and breaks the two-pane symmetry by an even larger margin. (See screenshot 2 — the same screen at MacBook resolution; the filter row has wrapped to two rows of chips.)

3. **Timeline turn cards left-align everything.** Inside `.tl-card-head`, the per-card layout today is:
   ```
   [Agent chip] [turn N] [Q] [D] [I] [C] <spacer> [status check] [chevron]
   ```
   The category counter chips (Q/D/I/C) follow the turn label on the left, then a flexbox `<span className="spacer" />` shoves the status check + chevron to the right. The right edge of the card has only two elements; the four counter chips are visually anchored to the turn label, not to the status. The user-stated intent is the inverse: the counters should hang off the right-aligned status check so eye-tracking down a column of cards reads a stable Q/D/I/C/✓ stack on the right edge, with the left edge holding only `[Agent] [Turn N]`.

All three defects are CSS / markup-only. There is no protocol, contract, or backend change.

---

## 2. Goals

1. **Both panes' header bars share an identical height in wide mode.** `.crit-filter-row` and `.tl__tabs` both render at the same `min-height` (55 px), with chips vertically centered. The seam under the two-pane chrome reads as a single horizontal rule from screen edge to screen edge.

2. **The critique filter row stays single-row at MacBook width.** Below the existing `1499 px` narrow-desktop breakpoint, the four kind-filter chips (Questions / Disagreements / Issues / Comments / All) collapse to **icon + count only** — the textual label is hidden, the category bubble and the numeric value remain. The three status chips (Open / Resolved / Drift) and the two agent chips (Claude / GPT) keep their full labels (they have no glyph) but pack tighter: the two `.crit-filter-spacer` separators shrink, and the inter-chip `gap` narrows. End result: the entire row fits on a single line at ≥ 1024 px viewport width and remains the same 55 px height as the tabs strip.

3. **Timeline turn cards split into a left group and a right group.** `.tl-card-head` becomes a `space-between` flex container. The left group is `[Agent chip] [turn N or "brief"]`. The right group, anchored to the right edge, is `[Q] [D] [I] [C] [status check] [chevron]`. Reading order from left to right on a single card: identity → counters → status → expand affordance.

4. **No regressions to existing behaviors.** Filter chip click handlers, hover tooltips, dim/active states, status-chip behavior, chevron toggle, click-to-expand on cards — all unchanged. Keyboard focus order on the cards still walks left → right.

---

## 3. Non-goals

- **No new chip variants in `shared.jsx`.** The label-hide behavior is done via a CSS modifier (`.crit-filter-row[data-compact="true"] .chip-label { display: none }`) gated by a `@media` rule, not by a new `<Chip compact>` prop. This keeps the chip primitive single-purpose and the responsive behavior local to the filter row.
- **No change to filter chip ordering, counts, or click semantics.** Q/D/I/C/All/Open/Resolved/Drift/Claude/GPT in that order, same `setKindFilter` / `setStatusFilter` / `setAgentFilter` handlers.
- **No change to the timeline turn card chip content.** Same Agent chip, same activity label, same Q/D/I/C counter chips with the same `value/add/sub/dim` props and same `dispatchCritiqueJump` click. Only the **layout** of those existing chips changes.
- **No change to `.tl__tabs` height.** It already reads 55 px; the critique row matches it, not the other way around. (Bumping tabs would ripple into spec 0107 / 0110 chrome contracts.)
- **No change to `.crit-card-head` (critique pane cards).** The user's screenshot 3 is about the **timeline** card head only; critique-side cards keep their existing layout.
- **No new breakpoint constant.** Reuse the existing `max-width: 1499px` breakpoint already in use at `components.css:902` (`.agent-input` grid collapse). Keeping a single narrow-desktop breakpoint avoids breakpoint sprawl.
- **No mobile/sub-900 px treatment.** The run-detail screen is desktop-only; the breakpoint is "wide desktop vs laptop", not "desktop vs phone". A future spec can add a sub-900 px mode if needed.

---

## 4. Current-state audit

### 4.1 — The two header bars (defects 1 and 2)

| Element | File | Lines | Current CSS / JSX |
|---|---|---|---|
| Critique filter row JSX | [run-detail.jsx:6115-6190](src/dual_research/ui/static/run-detail.jsx) | 6115–6190 | `<header className="bar2 crit-filter-row">` with 10 `<Chip>` children + 2 `<span className="crit-filter-spacer" />` separators |
| `.crit-filter-row` CSS | [components.css:678-683](src/dual_research/ui/static/components.css) | 678–683 | `display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 10px 14px; border-bottom: 1px solid var(--md-outline-hair);` — no `min-height` |
| `.crit-filter-spacer` CSS | [components.css:684-686](src/dual_research/ui/static/components.css) | 684–686 | `width: 12px; height: 1px; flex: 0 0 12px;` |
| Tabs strip JSX | [run-detail.jsx:804-820](src/dual_research/ui/static/run-detail.jsx) | 804–820 | `<div className="tl__tabs"><div className="tl__tabs-inner">…</div></div>` |
| `.tl__tabs` CSS | [components.css:1993-2001](src/dual_research/ui/static/components.css) | 1993–2001 | `display: flex; align-items: center; gap: 8px; padding: 10px 20px; min-height: 55px; flex-shrink: 0;` |

Measured height delta on wide viewport: `55 − 45 = 10 px`. The seam under the two-pane chrome is visibly stepped.

### 4.2 — Timeline turn card head (defect 3)

| Element | File | Lines | Current order |
|---|---|---|---|
| `.tl-card-head` JSX | [run-detail.jsx:1096-1159](src/dual_research/ui/static/run-detail.jsx) | 1096–1159 | `[Agent chip]` → `[Turn label]` → `[Q,D,I,C]` → `<span className="spacer" />` → `[TlStatusChip]` → `[Chevron]` |
| `.tl-card-head` CSS | [components.css:654-658](src/dual_research/ui/static/components.css) | 654–658 | `display: flex; align-items: center; gap: 6px; flex-wrap: wrap;` and `.spacer { flex: 1; min-width: 8px; }` |

The spacer at line 1148 sits **after** the Q/D/I/C chips, which is why they hug the turn label rather than the status. Moving the spacer to sit immediately after the turn/brief chip (i.e. before the `.map(chipCategories)` block) flips counters from the left group to the right group.

---

## 5. Proposed change

### 5.1 — Header height parity (`components.css`)

In the spec-0119 §8.3 block (around line 678), update `.crit-filter-row`:

```css
.crit-filter-row {
  display: flex; align-items: center; gap: 8px;
  flex-wrap: nowrap;                /* was: wrap — wrapping is the bug */
  padding: 10px 14px;
  min-height: 55px;                 /* NEW — matches .tl__tabs */
  border-bottom: 1px solid var(--md-outline-hair);
}
```

`flex-wrap: nowrap` prevents the small-screen wrap-and-grow on its own; the 5.2 compaction is what makes nowrap fit.

### 5.2 — Narrow-desktop compaction (`components.css`)

Append a new media block immediately after the `.crit-filter-row` rules (so the cascade is local and the override is easy to read):

```css
/* Spec 0124 — at narrow-desktop width the filter row would otherwise
   wrap to two rows. The four kind-filter chips have a category-bubble
   glyph + numeric value that read on their own; their textual label is
   redundant signal at this width. The status and agent chips have no
   glyph so they keep their labels but pack tighter via reduced gap and
   thinner separators. The 1499 px breakpoint matches the existing
   narrow-desktop rule at line 902. */
@media (max-width: 1499px) {
  .crit-filter-row {
    gap: 4px;
    padding: 10px 10px;
  }
  /* Hide labels on the kind-filter chips (the first cluster, before
     the first spacer). Identified via the absence of leadingDot /
     leadingIcon — kind chips are the only ones with a categoryBubble. */
  .crit-filter-row > .chip[data-category-bubble] .chip-label,
  .crit-filter-row > .chip[data-category-bubble='all'] .chip-label {
    display: none;
  }
  .crit-filter-spacer {
    width: 6px; flex: 0 0 6px;
  }
}
```

The `data-category-bubble` selector requires the `<Chip>` primitive to forward its `categoryBubble` prop (and the `"all"` fallback) to a DOM attribute. If the chip doesn't already do this, the implementation adds a one-line `data-category-bubble={categoryBubble ?? (label === 'All' ? 'all' : undefined)}` passthrough in `shared.jsx`. (Alternative if that's invasive: add a one-off `data-kind-filter="true"` attribute on the kind-filter chips in the JSX at `run-detail.jsx:6123-6142` and key the CSS off that. Implementer's call — both produce the same visible result. Recommend the data-attribute on the Chip primitive since it's reusable.)

### 5.3 — Timeline card right-alignment (`run-detail.jsx` + `components.css`)

**JSX change** at `run-detail.jsx:1096-1159`: move the `<span className="spacer" />` from line 1148 to immediately after the activity/brief chip and before the `chipCategories.map(...)`. New order:

```jsx
<header className="tl-card-head">
  {agent && <Chip … />}                      {/* agent chip */}
  {!agent && item.kind === 'input'
    ? <Chip … label="brief" />
    : <Chip mono tone="neutral" label={activityLabel.toLowerCase()} />}

  <span className="spacer" />                {/* MOVED — was on line 1148 */}

  {showCategoryChips && chipCategories.map((cat) => { … })}
  <TlStatusChip item={item} isLive={isLive} />
  <span className="tl-card-chev" … ><Icon.Chevron /></span>
</header>
```

**CSS change** at `components.css:654-658`: keep `.tl-card-head` as a flex row but tighten gap-handling so the right-group chips read as a cluster:

```css
.tl-card-head {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  cursor: pointer;
}
.tl-card-head > .spacer { flex: 1; min-width: 8px; }
/* NEW — tighter gap inside the right cluster so the Q/D/I/C/✓ row
   reads as one stack, not five floating chips. */
.tl-card-head > .spacer ~ * { /* every sibling after the spacer */ }
```

(The `~ *` sibling selector is illustrative — the implementation may prefer to wrap the right group in a `<div className="tl-card-head__right">` with `display: inline-flex; gap: 4px; align-items: center;`. Either approach is fine; the wrapper is slightly more explicit and easier to read. Recommend the wrapper.)

If the wrapper approach is used, the JSX becomes:

```jsx
<header className="tl-card-head">
  {agent && <Chip … />}
  <Chip … />
  <span className="spacer" />
  <div className="tl-card-head__right">
    {showCategoryChips && chipCategories.map((cat) => { … })}
    <TlStatusChip item={item} isLive={isLive} />
    <span className="tl-card-chev" … ><Icon.Chevron /></span>
  </div>
</header>
```

And the CSS:

```css
.tl-card-head__right {
  display: inline-flex; align-items: center; gap: 4px;
  margin-left: auto;
}
```

(`margin-left: auto` also right-aligns the cluster; with the wrapper the explicit `.spacer` becomes optional. Pick one mechanism — wrapper + `margin-left: auto`, or spacer + sibling cluster. Recommend the wrapper for readability.)

### 5.4 — Cache bust

Bump the static-asset query string in `app.jsx` from the current `?v=0123a` to `?v=0124a` so the new CSS lands without users having to hard-reload.

---

## 6. Visual references

The three screenshots in the originating conversation are the visual spec:

1. **Wide-screen state (defect 1 + intended fix).** Header bar on the right is shorter than on the left. Intended fix: both bars same 55 px height, chips vertically centered, seam under chrome flush.
2. **Small-screen state (defect 2 + intended fix).** Same screen at MacBook width — filter row has wrapped to two rows. Intended fix: kind-filter chips become `[bubble] [count]` (no label), status/agent chips keep labels but pack tighter, whole row stays on a single line at 55 px.
3. **Timeline card state (defect 3 + intended fix).** Current: `[Claude] [turn 2] [Q] [D] [✓]` left-clustered. Intended: `[Claude] [turn 2] ............... [Q] [D] [✓] [>]` with counters and status hanging off the right edge as a single right-aligned cluster.

The implementation should produce a side-by-side before/after screenshot pair (wide and narrow viewports) and attach them to the PR.

---

## 7. Out of scope

- The critique pane card heads (`.crit-card-head`). The user explicitly scoped the alignment change to the **timeline** side; critique-side cards keep the spacer-after-id layout from spec 0119 §8.4.
- The Bar 1 (critique pane title bar) height. The user did not flag it. It's `padding: 10px 20px` ≈ 44 px today and is visually fine because it sits across from the timeline title (also `bar1`-class).
- Any new chip primitive variants. The compaction is a local CSS override, not a primitive change.
- Sub-900 px viewport behavior. The two-pane screen is desktop-only.
- Touch / hover affordance changes. Click handlers and tooltips are unchanged.

---

## 8. Test plan

- [ ] Open a recent run with cross-review (e.g. the pv-backend-language-brief run from the originating screenshots). On a viewport ≥ 1500 px:
  - Visually confirm `.crit-filter-row` and `.tl__tabs` are pixel-identical in height (DevTools → Computed → `height` reads 55 px for both).
  - Visually confirm chips are vertically centered.
  - Visually confirm the seam under the two-pane chrome is a single straight line, not stepped.
- [ ] Resize the same window to ~ 1280 px (MacBook-13 width):
  - Visually confirm the kind-filter chips show as `[bubble] [count]` only (no "Questions"/"Disagreements"/"Issues"/"Comments"/"All" text).
  - Visually confirm the status and agent chips still show their text labels.
  - Visually confirm the entire filter row is on a single line.
  - Visually confirm both bars are still 55 px.
- [ ] Resize down to ~ 1024 px and confirm the row still fits on one line. If it doesn't, narrow the breakpoint or tighten gaps further; do not let it wrap.
- [ ] Resize back up past 1500 px and confirm the kind-filter labels reappear.
- [ ] On any phase row in the timeline:
  - Visually confirm cards now read `[Agent] [turn N] ... [Q] [D] [I] [C] [✓] [>]` with the right cluster pinned to the right edge.
  - Click each existing affordance — agent chip, turn chip, each counter chip, status chip, the card body — and confirm all click handlers fire as before (chip jumps to critique pane; card expands; etc.).
  - Tab through the card with the keyboard and confirm focus order is unchanged (or, if the right-group wrapper changes DOM order, that focus order still reads naturally left → right).
- [ ] Light-mode and dark-mode parity check on all three changes.
- [ ] Regression scan: load the Compare page, the Search page, the How-It-Works page, and a critique-side card expansion — confirm no incidental visual change (the CSS scope is `.crit-filter-row`, `@media`, `.tl-card-head` — should be inert elsewhere).

---

## 9. Risks

- **`flex-wrap: nowrap` + compaction not aggressive enough at some viewport sizes.** If `Drift` or `GPT` clips at, say, 1100 px, the test plan catches it and the fix is either a tighter `gap` or a slightly more conservative breakpoint. The user has only two effective viewport sizes (wide monitor and MacBook), so the practical width range to test is narrow.
- **`data-category-bubble` chip primitive change creates a passthrough not in use elsewhere.** Mitigation: the attribute is inert when absent (no CSS selector matches it outside `.crit-filter-row`). Alternative: use the `data-kind-filter` on-the-call attribute path described in 5.2.
- **Timeline card focus order ripples to keyboard users** if the right-group wrapper changes DOM order. Mitigation: the wrapper preserves source order (chips were already after the spacer in the source), so the wrapper move is invisible to focus traversal. Confirm in the test plan anyway.
- **Cache busting forgotten.** Implementer must remember to bump the `?v=` query string; without it users see stale CSS. Already in the test plan as the first thing to verify in DevTools.

---

## 10. Open questions

None — the visual intent is fully specified by the three screenshots and the prose above. Implementer choice points (data-attribute on Chip vs on the call site; wrapper vs spacer-+-sibling-selector for the right group) are noted inline in §5 with a recommendation.
