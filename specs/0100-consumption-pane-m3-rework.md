---
spec: 0100
title: Consumption pane full rework — collapsed + unfolded with sub-rows + uniform width across phases with round chip above card + sticky bottom legend
label: bug
version-bump: MINOR
status: proposed
target-version: 0.74.0
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0100 — Consumption pane full rework

> Ship bucket: **Composed**
> Depends on: **0092, 0093, 0094**
> Complexity: **L**
> Targeted version bump: **MINOR** (consumption pane is the largest visible-IA change in the rebuild; the four issues together restructure what the pane shows and how)

## 1. Goal

Replace the existing consumption-row layout with the canonical M3
`ccx` card anatomy in all three forms — collapsed (header trio +
total-in bar + total-out bar), unfolded (sub-rows under each
total + totals block + cache reuse marker + striped overlay), and
uniform-across-phases (cards keep one width; the round label sits
**above** the card as a small chip). Add the sticky bottom legend
inside the pane (not the viewport). Resolves Issues 12, 13, 14, 15.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the
  reworked consumption block: `.ccx` + `.ccx-header` +
  `.ccx-icon.{a,b}` + `.ccx-header .nm` + `.ccx-header .stats` +
  `.ccx-header .stats .{sep,pct}` + `.ccx-header .chev` per
  [v2-m3-page.css:803-833](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.ccx-bar-row` + `.ccx-bar-row.is-total` + `.ccx-sub-row` +
  `.ccx-bar` + `.ccx-bar.thin` + `.ccx-bar .fl` (with all the
  agent / sub-bucket variants: `.in`, `.out`, `.in-b`, `.out-b`,
  `.sys`, `.hist`, `.round`, `.tools`, `.web`, `.reason`,
  `.resp`, `.toolc`) + `.ccx-bar .reuse` (diagonal stripe
  overlay) per
  [v2-m3-page.css:835-892](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.ccx-divider` + `.ccx-section-spacer` + `.ccx-totals` +
  `.ccx-totals .line` + `.ccx-totals .line .{v,l}` +
  `.ccx-totals .line.is-{savings,grand}` per
  [v2-m3-page.css:893-913](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.cards-2up` grid (1fr 1fr ≥ 1100 px; 1fr below); `.round-label`
  + `.round-label .pcode`; `.phase-group-head` per
  [v2-m3-page.css:915-931](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.reuse-mark` + `.reuse-mark::after` (hover tooltip) +
  `.cache-mark` + `.web-mark` per
  [v2-m3-page.css:1074-1137](docs/design-system-v2/assets/styles/v2-m3-page.css).
  **Add a new `.ccx-pane` wrapper rule** for the sticky-bottom-
  legend container: `position: sticky; bottom: 0; background:
  var(--md-surface-container-high); border-top: 1px solid
  var(--md-outline-hair); box-shadow: var(--md-elev-1); padding:
  var(--md-sp-3) var(--md-sp-6);` — this is the Issue 15
  contract.
- `src/dual_research/ui/static/run-detail.jsx` — rewrite the
  consumption render path. Concretely, replace the existing
  `ConsumptionView` / `ConsumptionRow` / `ConsumptionCard`
  family (lines 1410-2382) with the new `ccx` anatomy:
  - **Collapsed card** (Issue 12): header is a single row with
    three numeric stats right-aligned to the bar's left edge —
    `(provider icon)(provider name) … (N kt total · $X · (P% of
    1M))`. Below the header: two bar rows, `total in` and
    `total out`, each labelled left, bar centre, count right.
    No input-cost / output-cost / total-cost line in the
    collapsed state. The `.ccx-bar` for `total in` uses the
    agent's primary colour at full opacity (`.fl.in` for Claude,
    `.fl.in-b` for GPT); `total out` uses the same hue at 55 %
    opacity (`.fl.out` / `.fl.out-b`).
  - **Unfolded card** (Issue 13): the collapsed view stays at
    the top, then expands downward with:
    1. `.ccx-bar-row.is-total` for `total in`.
    2. `.ccx-divider` (single 1 px hairline).
    3. One `.ccx-sub-row` per recorded input bucket (system
       prompt, conversation history, round context, tool
       definitions, web sources). Each carries a thin bar
       (`.ccx-bar.thin`) using the appropriate per-bucket
       colour (`.fl.sys`, `.fl.hist`, `.fl.round`, `.fl.tools`,
       `.fl.web`). The bar's diagonal-stripe overlay
       (`.ccx-bar .reuse`) renders the cached-reused portion;
       width: matches the reused-token share of the bar. To
       the left of the count, a `.reuse-mark` chip shows the
       reuse multiplier (`×5.9`, `cached`, `6q`) with a
       `data-tooltip` carrying the dollar savings.
    4. `.ccx-totals` block with five lines, in order:
       `N input tokens · billed`, `$X input cost`,
       `$Y web search · N queries` (only if any web search),
       `−$Z cache savings · ×N reuse on Mkt` (`.line.is-
       savings`, only if any reuse), `$T total input`
       (`.line.is-grand`, bold rule above).
    5. `.ccx-section-spacer` (8 dp).
    6. `.ccx-bar-row.is-total` for `total out`.
    7. `.ccx-divider`.
    8. One `.ccx-sub-row` per recorded output bucket
       (reasoning, response, tool calls).
    9. `.ccx-totals` block: `N output tokens`, `$X output
       cost`, `$T total output` (`.line.is-grand`).
  - **Uniform-across-phases** (Issue 14): the card never
    changes width between phases. The round label rendered
    **above** the card as `<div class="round-label"><span
    class="pcode">P2</span><span>·</span><span>round 1 of 6
    soft</span></div>`. The phase grouping uses
    `<div class="phase-group-head">P2 · Negotiate</div>` above
    each pair of cards. Verify by capturing P0 + P1 + P2 stacked
    and confirming every `.ccx` card has the same computed
    width.
  - **Sticky bottom legend** (Issue 15): wrap the consumption
    body in `<div class="ccx-pane">`. The body scrolls;
    immediately above the body's footer, render a
    `<footer class="ccx-pane__legend">` carrying agent colour
    swatches, the bar-overlay legend (solid = current charge,
    striped = cache reuse, accent = web search), and short
    text legend lines. The legend is `position: sticky;
    bottom: 0;` — the body content scrolls under it.
- `src/dual_research/ui/static/run-detail.jsx` — also update
  `ConsumptionLegend` (line 2383) so the new sticky-bottom
  version reads from the same legend content but renders
  inside `.ccx-pane__legend` instead of as a free-floating
  block below the cards.
- `pyproject.toml` — `0.73.2` → `0.74.0`.

## 3. Material 3 anatomy

- `#consumption` — verbatim source. Three forms (collapsed,
  unfolded, uniform across phases), sticky bottom legend.
- `#elevation` — cards default to elevation-1 (the `.ccx` base
  rule), lift to elevation-2 on hover via the Spec 0094 rule.
- `#fmt` — token counts in `tnum, ss01` tabular numerics; cost
  with 3 decimals; the `(N % of 1M)` chip in the header.

**Inline HTML structure** (copied from
[Design System v2.html · #consumption](docs/design-system-v2/assets/Design%20System%20v2.html)
lines 1099-1220, normalised for the live app):

```html
<!-- COLLAPSED — Issue 12 -->
<article class="ccx">
  <header class="ccx-header">
    <span class="ccx-icon a">C</span>
    <span class="nm">Claude</span>
    <span class="stats">
      <span>72.2kt total</span><span class="sep">·</span>
      <span>$0.2846</span><span class="sep">·</span>
      <span class="pct">7.2% of 1M</span>
    </span>
    <span class="chev"><span class="ms ms-20">expand_more</span></span>
  </header>
  <div class="ccx-bar-row is-total">
    <span class="lbl">total in</span>
    <div class="ccx-bar"><div class="fl in" style="width:71%"></div></div>
    <span class="num">71.0kt</span>
  </div>
  <div class="ccx-bar-row is-total">
    <span class="lbl">total out</span>
    <div class="ccx-bar"><div class="fl out" style="width:1.2%"></div></div>
    <span class="num">1.2kt</span>
  </div>
</article>

<!-- UNFOLDED — Issue 13. Same width as collapsed. -->
<article class="ccx">
  <header class="ccx-header">
    <span class="ccx-icon a">C</span>
    <span class="nm">Claude</span>
    <span class="stats">…</span>
    <span class="chev"><span class="ms ms-20">expand_less</span></span>
  </header>

  <!-- total in (header bar) -->
  <div class="ccx-bar-row is-total">
    <span class="lbl">total in</span>
    <div class="ccx-bar">
      <div class="fl in" style="width:82%"></div>
      <div class="reuse" style="left:0;width:68%"></div>
    </div>
    <span class="num">411.9kt</span>
  </div>
  <div class="ccx-divider"></div>

  <!-- sub-rows · one per recorded input bucket. Striped overlay where reused. -->
  <div class="ccx-sub-row">
    <span class="lbl">system prompt</span>
    <div class="ccx-bar thin"><div class="fl sys" style="width:2%"></div></div>
    <span class="num">8.2k</span>
  </div>
  <div class="ccx-sub-row">
    <span class="lbl">conversation history</span>
    <div class="ccx-bar thin">
      <div class="fl hist" style="width:76%"></div>
      <div class="reuse" style="left:0;width:65%"></div>
    </div>
    <span class="num">
      <span class="reuse-mark" tabindex="0" data-tooltip="Cache reuse · ×5.9 · 320.1k tokens read from cache · saved $0.4187">
        <span class="ms" aria-hidden="true">cached</span>×5.9
      </span>
      <span>320.1k</span>
    </span>
  </div>
  <!-- … round context · tool definitions · web sources … -->

  <!-- input totals -->
  <div class="ccx-totals">
    <div class="line"><span class="v">411,902</span><span class="l">input tokens · billed</span></div>
    <div class="line"><span class="v">$0.6059</span><span class="l">input cost</span></div>
    <div class="line"><span class="v">$0.0600</span><span class="l">web search · 6 queries</span></div>
    <div class="line is-savings"><span class="v">−$0.4187</span><span class="l">cache savings · ×5.9 reuse on 345.0k</span></div>
    <div class="line is-grand"><span class="v">$0.6659</span><span class="l">total input</span></div>
  </div>

  <div class="ccx-section-spacer"></div>

  <!-- total out + sub-rows + output totals (same pattern) -->
  <div class="ccx-bar-row is-total">
    <span class="lbl">total out</span>
    <div class="ccx-bar"><div class="fl out" style="width:7.2%"></div></div>
    <span class="num">7.2kt</span>
  </div>
  <div class="ccx-divider"></div>
  <div class="ccx-sub-row"><span class="lbl">reasoning</span><div class="ccx-bar thin"><div class="fl reason" style="width:3.5%"></div></div><span class="num">3.5k</span></div>
  <div class="ccx-sub-row"><span class="lbl">response</span><div class="ccx-bar thin"><div class="fl resp" style="width:2.8%"></div></div><span class="num">2.8k</span></div>
  <div class="ccx-sub-row"><span class="lbl">tool calls</span><div class="ccx-bar thin"><div class="fl toolc" style="width:0.9%"></div></div><span class="num">0.9k</span></div>

  <div class="ccx-totals">
    <div class="line"><span class="v">7,183</span><span class="l">output tokens</span></div>
    <div class="line"><span class="v">$0.1084</span><span class="l">output cost</span></div>
    <div class="line is-grand"><span class="v">$0.1084</span><span class="l">total output</span></div>
  </div>
</article>

<!-- UNIFORM ACROSS PHASES — Issue 14. Round label ABOVE the card. -->
<div class="phase-group-head">P2 · Negotiate</div>
<div class="cards-2up">
  <div>
    <div class="round-label"><span class="pcode">P2</span><span>·</span><span>round 1 of 6 soft</span></div>
    <article class="ccx">…</article>
  </div>
  <div>
    <div class="round-label"><span class="pcode">P2</span><span>·</span><span>round 1 of 6 soft</span></div>
    <article class="ccx">…</article>
  </div>
</div>

<!-- STICKY LEGEND — Issue 15. -->
<div class="ccx-pane">
  <div class="ccx-pane__body">… cards scroll here …</div>
  <footer class="ccx-pane__legend">
    <span class="legend-row">
      <span class="legend-sw a"></span><span>Claude</span>
      <span class="legend-sw b"></span><span>GPT</span>
    </span>
    <span class="legend-sep">|</span>
    <span class="legend-row">
      <span class="legend-sw solid"></span><span>current charge</span>
      <span class="legend-sw striped"></span><span>cache reuse</span>
      <span class="legend-sw web"></span><span>web search</span>
    </span>
  </footer>
</div>
```

## 4. Notion issues addressed

1. **Issue 12 — Collapsed consumption card data points must change.**
   Source: `docs/design-system-v2/notion-issues/screenshots/12-collapsed-consumption.png`.
   Per § 2: collapsed card has three rows — header trio + total
   in bar + total out bar. No input/output/total cost line in
   the collapsed state.
2. **Issue 13 — Unfolded consumption card data points must
   change.** Source: `…/13-unfolded-consumption.png`. Per § 2:
   unfolded card adds sub-rows under total-in and total-out,
   each with its own thin bar and reuse marker; then per-section
   totals blocks with cache-savings and grand-total lines. Striped
   overlay shows cache reuse on the bar; the `.reuse-mark` chip
   to the left of the count carries the multiplier + hover
   tooltip.
3. **Issue 14 — Consumption cards change horizontal size between
   phases.** Source: `…/14-consumption-size.png`. Resolution:
   `.ccx` width is fixed by its container's `.cards-2up` grid
   (1 fr / 1 fr ≥ 1100 px; 1 fr below). Width does not vary by
   phase. Round label renders **above** the card as
   `.round-label`, never inside the header. Phase grouping
   labels (`.phase-group-head`) above each phase's pair.
   Verified by computed width parity across P0 / P2 / P4.
4. **Issue 15 — Consumption legend should be a sticky bottom bar.**
   Source: `…/15-sticky-legend.png`. Resolution: wrap the body
   in `.ccx-pane` and render the legend as a `position: sticky;
   bottom: 0;` footer inside the same scroll container. The
   legend stays visible while cards scroll under it.

## 5. Acceptance criteria

- [ ] **Issue 12.** Collapsed `.ccx` card renders exactly three
      rows: header trio + total-in + total-out. No input/output/
      total cost line in the collapsed body.
- [ ] **Issue 13.** Unfolded `.ccx` card renders the full
      anatomy in §3 — sub-rows under total in, input totals
      block, spacer, total out, sub-rows under total out, output
      totals block. Cache reuse renders as the diagonal-stripe
      overlay; the `.reuse-mark` chip shows the multiplier and
      reveals the dollar saving on hover/focus.
- [ ] **Issue 14.** Every `.ccx` card across P0 → P4 reports
      the same computed `width` value. The round label renders
      as `.round-label` above the card; no round metadata
      inside the card header.
- [ ] **Issue 15.** Scrolling the consumption body keeps the
      legend visible; the legend container resolves
      `position: sticky` and `bottom: 0` in DevTools.
- [ ] The hover tooltip on `.reuse-mark` renders the dollar
      savings sentence verbatim (`Cache reuse · ×5.9 · 320.1k
      tokens read from cache · saved $0.4187` template).
- [ ] No invented buckets: if the backend doesn't emit a
      particular sub-bucket (e.g. `tool definitions`), that sub-
      row is omitted and the totals block recomputes from what
      is available. (Verified by running a fixture where one
      bucket is missing.)
- [ ] Hover on the card lifts elevation-1 → elevation-2 (the
      Spec 0094 rule fires). Hover on the legend does not lift.
- [ ] All three forms render correctly in dark and light without
      per-theme overrides.

## 6. Visual verification matrix

- `2200×1300 dark` — route `#/runs/<run with P0..P4 and at
  least one round with cache reuse>`. Capture (a) collapsed
  cards row, (b) one unfolded card with sub-rows + cache-reuse
  stripe + totals block, (c) the full pane scrolled with the
  sticky legend visible.
- `2200×1300 light` — same.
- `1400×900 dark` — same. Verify the `.cards-2up` grid collapses
  to 1 fr below 1100 px.
- `1400×900 light` — same.
- `820×1180 dark` — single-column; verify all three forms still
  render with their column intact.
- `820×1180 light` — same.

All six required. Issues 12-15 together constitute the largest
visible-IA shift in the rebuild; regressions here are
high-leverage.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database.
- [ ] No emoji as icons.
- [ ] No off-grid spacing — card padding 14 / 16 dp, bar height
      10 dp (thin: 6 dp), totals block padding 10 / 12 dp.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides — the diagonal-stripe overlay
      switches its mix-blend-mode per theme but reads from
      `body.light .ccx-bar .reuse` rule already covered in the
      CSS we mirror.
- [ ] Reduced-motion contract preserved — the chevron
      rotation on collapse reads `--md-easing-emphasized` at
      `--md-dur-short-3`; killed under `reduce`.
- [ ] Focus ring visible on every focusable (`.ccx-header
      .chev`, `.reuse-mark` for its tooltip).
- [ ] **Issue 12 anti-pattern:** no cost line in collapsed card.
- [ ] **Issue 13 anti-pattern:** no quote of any per-bucket
      data outside its sub-row + count cell.
- [ ] **Issue 14 anti-pattern:** no card width that varies by
      phase; no round chip inside the header.
- [ ] **Issue 15 anti-pattern:** legend rendered below the cards
      (free-floating); legend must be sticky inside the pane.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0099-timeline-pane-m3-rework.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The pane reads existing `usage` records (per-bucket
token counts, costs, cache-reuse multipliers, web-search counts)
that the backend already emits. **Degrade gracefully:** if a
sub-bucket is not present (e.g. older runs without
`tool_definitions` counts), omit that `.ccx-sub-row` and
recompute the input totals block from what IS available. Never
fabricate a count; never propose adding a backend field. If the
backend doesn't emit a `cache_savings_usd`, omit the `.line.is-
savings` line in the totals block rather than computing one from
client-side estimation.

## 11. CSS class anchor list

```
.ccx                                    → #consumption (card container)
.ccx-header                             → #consumption (header trio — Issue 12)
.ccx-icon.{a,b}                         → #consumption (agent initial circle)
.ccx-header .nm, .stats, .sep, .pct     → #consumption (provider + numeric stats + % of 1M)
.ccx-header .chev                       → #consumption (collapse / expand chevron)

.ccx-bar-row, .ccx-bar-row.is-total     → #consumption (total in / total out)
.ccx-sub-row                            → #consumption · Issue 13 (per-bucket sub-row)
.ccx-bar, .ccx-bar.thin                 → #consumption (bar tracks)
.ccx-bar .fl + variants                 → #consumption (per-bucket fill colors)
.ccx-bar .reuse                         → #consumption · Issue 13 (diagonal-stripe overlay)

.ccx-divider                            → #consumption (1 px hairline between section header and sub-rows)
.ccx-section-spacer                     → #consumption (vertical spacer between input and output sections)
.ccx-totals                             → #consumption · Issue 13 (totals block)
.ccx-totals .line, .v, .l               → #consumption (totals line anatomy)
.ccx-totals .line.is-savings            → #consumption (cache savings line, ok tint)
.ccx-totals .line.is-grand              → #consumption (grand total with bold rule above)

.reuse-mark, .reuse-mark::after         → #consumption · Issue 13 (multiplier chip + hover tooltip)
.cache-mark, .web-mark                  → #consumption (small inline marks)

.cards-2up                              → #consumption · Issue 14 (uniform pair grid)
.round-label, .round-label .pcode       → #consumption · Issue 14 (round chip ABOVE the card)
.phase-group-head                       → #consumption · Issue 14 (phase grouping label)

.ccx-pane                               → #consumption · Issue 15 (scroll container)
.ccx-pane__body                         → #consumption (cards scroll under legend)
.ccx-pane__legend                       → #consumption · Issue 15 (sticky bottom legend)
```
