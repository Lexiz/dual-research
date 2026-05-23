---
kind: dev
spec: "0180"
slug: consumption-card-v2-anatomy
title: "Fix: Consumption card V2 anatomy — split combined Total tokens bar into total-input + total-output, add output totals block, move cache-savings line"
type: bug
label: bug
version_bump: PATCH
target_version: "1.36.3"
status: deployed
queue_position: 1
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T22:55:00Z"
started_at: "2026-05-23T10:30:44Z"
merged_at: "2026-05-23T10:50:09Z"
deployed_at: "2026-05-23T10:54:28Z"
pr: "https://github.com/Lexiz/dual-research/pull/210"
handover: "handoffs/2026-05-23-spec-0180-consumption-card-v2-anatomy.md"
failure_step: ""
source_session: bug-spec-batch-2205-claude
promoted_from_draft: ""
---

# Spec 0180 — Fix: Consumption card V2 anatomy

> **Type:** bug  |  **Severity:** P1  |  **Affects:** every Consumption tab card across every run / every phase / every round. The collapsed-state header + bar surface is wrong (single combined bar instead of input + output), the unfolded anatomy is wrong (no output totals block, cache-savings mislocated, output bar sits before the input totals), and the rendering carries heavy inline-style usage that bypasses the DS token contract.
> **Bump:** PATCH — bug fix; no schema, no API, no new wire format. Net source diff ~150 LOC across `CcxCard`, ~50 LOC of new CSS classes (with mirrors in both live + DS-canonical files), 1 sub-section added to `design-system/SPEC.md`. No new primitive.
> **Evidence:** Notion bug-batch page "Specs 2205 (Claude)" Bug 5 (`https://www.notion.so/Specs-2205-Claude-36899f3e507f802a90f6df0566d9704b`). Design-system reference: [design-system/notion-issues/ISSUES.md](design-system/notion-issues/ISSUES.md) Issue 12 (collapsed) and Issue 13 (unfolded), with anchor screenshots `design-system/notion-issues/screenshots/12-collapsed-consumption.png` and `13-unfolded-consumption.png`. Spec 0146 ("Consumption card visual rework") landed the input-side totals block but never landed the parallel output totals block. Spec 0148 added cache-savings rendering inside the input totals — that location turns out to be wrong; per Issue 13 the cache-reuse signal belongs in the **output** totals block. Both pieces are visible in [src/dual_research/ui/static/run-detail.jsx](src/dual_research/ui/static/run-detail.jsx) lines 2999-3145 today.

---

## 1. Reproduction

**Environment.** Live app `https://dual-research-alex.fly.dev`. Any run with a Consumption tab populated (the anchor run `20260521-010637-dvs-backend-language-choice` covers Phase 0 / 1 / 2 / 4 — pick any Phase 0 card to start, since Phase 0 cards are the simplest baseline). Viewport 1440 × 900 or wider.

**Steps.**

1. Open a run detail page; switch to the **Consumption** tab.
2. Scan the collapsed cards — header line at the top of each card.

**Expected:** (Per Issue 12) Each collapsed card shows three rows:
- Header: `[provider icon] [provider name] [total tokens] [total cost] ([X.X% of 1M])` — total tokens + total cost surfaced inline before the percentage.
- Bar 1: **total input bar** — input tokens visualised against the context window.
- Bar 2: **total output bar** — output tokens visualised against the same scale.

**Actual:** Each collapsed card shows:
- Header: `[provider icon] [provider name] (X.X% of 1M)` — no total tokens, no total cost inline. ([src/dual_research/ui/static/run-detail.jsx:2982-2995](src/dual_research/ui/static/run-detail.jsx:2982))
- Bar 1: a single combined `Total tokens` bar carrying `tokensIn + tokensOut` at the right edge. ([src/dual_research/ui/static/run-detail.jsx:2999-3014](src/dual_research/ui/static/run-detail.jsx:2999))
- Bar 2: nothing — the output side is invisible in the collapsed state.

3. Click the chevron to unfold the same card. Read the unfolded body top-to-bottom.

**Expected:** (Per Issue 13, top-to-bottom)

1. Total **input** bar (already visible from collapsed state).
2. Per-input rows — one row per recorded input piece, each with its own bar.
3. Divider.
4. **Input totals text block** — `total input tokens` · `total input cost` · `web search · N queries` (when applicable) · `total input cost` (grand).
5. Total **output** bar.
6. Per-output rows — `Reasoning` / `Response` / `Tool calls` when the split data exists.
7. Divider.
8. **Output totals text block** — `total output tokens` · `total output cost` · `web searches` (when applicable) · `cache savings · ×N reuse on Xkt` (moved here from the input side).

**Actual:**

1. Combined `Total tokens` bar at top (carrying both `tokensIn + tokensOut`). ([src/dual_research/ui/static/run-detail.jsx:2999-3014](src/dual_research/ui/static/run-detail.jsx:2999))
2. Cache-reuse signal line in mono text (collapsed-line, retained from spec 0051). ([src/dual_research/ui/static/run-detail.jsx:3017-3025](src/dual_research/ui/static/run-detail.jsx:3017))
3. Divider. ([src/dual_research/ui/static/run-detail.jsx:3031](src/dual_research/ui/static/run-detail.jsx:3031))
4. Per-phase input rows. ([src/dual_research/ui/static/run-detail.jsx:3035](src/dual_research/ui/static/run-detail.jsx:3035))
5. Divider. ([src/dual_research/ui/static/run-detail.jsx:3038](src/dual_research/ui/static/run-detail.jsx:3038))
6. Output header bar (combined "Output" line with `tokensOut` only — but it sits **before** the input totals block, not after). ([src/dual_research/ui/static/run-detail.jsx:3054-3076](src/dual_research/ui/static/run-detail.jsx:3054))
7. Per-output sub-rows (`Reasoning` / `Response` / `Tool calls`). ([src/dual_research/ui/static/run-detail.jsx:3078-3098](src/dual_research/ui/static/run-detail.jsx:3078))
8. **Mislocated** totals block carrying input tokens + input cost + web search + cache savings + total input grand. The cache-savings line lives inside the **input** totals — per Issue 13 it belongs in the **output** totals. ([src/dual_research/ui/static/run-detail.jsx:3103-3145](src/dual_research/ui/static/run-detail.jsx:3103))
9. **Missing entirely:** the second divider + the **output** totals text block. The card ends with the input-side grand total; the parallel output totals block does not exist.

The cumulative effect is that the user cannot read the output side of the card in the canonical "bar → rows → divider → totals" pattern that the input side already follows — the output side has no totals at all.

**Out-of-spec inline styling.** The bar-row grids use repeated inline `style={{ display: 'grid', gridTemplateColumns: 'minmax(140px, 28%) 1fr minmax(110px, max-content)', alignItems: 'center', gap: 10 }}` blobs at lines 2999-3003, 3055-3060, 3076-3098 — bespoke per-render-site values that should be a single named class per CLAUDE.md's DS-hygiene rules.

## 2. Root cause hypothesis

Spec 0118 redesigned the collapsed surface to a single combined `Total tokens` bar (replacing the earlier total-in / total-out pair) on the premise that one bar reads cleaner than two — but Issue 12 reverses that decision: the canonical V2 anatomy carries **both** input and output bars in the collapsed state, with the input bar acting as the "first thing you see on unfold" per Issue 13. The combined bar is the root structural error; everything downstream (totals layout, cache-savings placement, output-side surface invisibility in collapsed state) follows from that decision.

Concrete code anchors:

- **Header line.** [src/dual_research/ui/static/run-detail.jsx:2982-2995](src/dual_research/ui/static/run-detail.jsx:2982) — renders `<span class="hd-id">` (icon + name), `<span class="stats">` (percentage), `<span class="chev">` (chevron). No total-tokens / total-cost inline slot. Issue 12 §1 requires these between name and percentage.
- **Combined Total-tokens bar.** [src/dual_research/ui/static/run-detail.jsx:2999-3014](src/dual_research/ui/static/run-detail.jsx:2999) — `<div class="ccx-bar-row is-total">` with label "Total tokens", a single fill `<div class="fl {fillIn}" style={{ width: ${totalPct}% }}>` and a right-side stat `{fmt.tokens(totalTok)}t · {fmtCost1(cost)}`. `totalTok` combines input + output; `totalPct` is computed against the context window for the **sum**. This bar must split into two: a `total-input` bar (`tokensIn`) and a `total-output` bar (`tokensOut`), both rendered above the `{expanded && ...}` gate so they're visible in collapsed state.
- **Cache-reuse signal line (collapsed mono text).** [src/dual_research/ui/static/run-detail.jsx:3017-3025](src/dual_research/ui/static/run-detail.jsx:3017) — `{reuse.hasReuse && (<div class="mono">…)}`. With the cache-savings now belonging in the output totals (Issue 13), this collapsed-line mono text becomes redundant — drop it.
- **Output header bar.** [src/dual_research/ui/static/run-detail.jsx:3054-3076](src/dual_research/ui/static/run-detail.jsx:3054) — currently sits **between** the per-input rows and the totals block. Must move to **after** the input totals block per Issue 13's ordering.
- **Totals block (currently input-only, mis-carrying cache-savings).** [src/dual_research/ui/static/run-detail.jsx:3103-3145](src/dual_research/ui/static/run-detail.jsx:3103) — `<div class="ccx-totals">` with five `.line` rows. The cache-savings `.line` (inside the IIFE at lines 3125-3140) must move to the new output totals block.
- **Missing.** No JSX element exists today for the output divider + output totals block. Both must be added.
- **Inline-style hygiene.** Multiple inline `style={{ display: 'grid', gridTemplateColumns: 'minmax(140px, 28%) 1fr minmax(110px, max-content)', alignItems: 'center', gap: 10 }}` repetitions at 2999-3003, 3055-3060. These belong on a single named class (e.g. `.ccx-bar-row` already exists in CSS; the inline overrides are accidental duplication of what the class should already do — verify by reading the class rule in `src/dual_research/ui/static/components.css` and lifting any missing properties up there).

## 3. Fix

Six concrete sub-changes. All land in a single PR; per the bundle decision in §1d, splitting into multiple specs would create a linear dependency chain with no parallelism gain.

**DS citations.** The Consumption card is governed by [design-system/SPEC.md](design-system/SPEC.md) §4.something (Consumption pane — verify the exact section name at branch-cut; section 4 carries the per-pane composition rules and §4.x has the Consumption sub-section). The bar primitive and chip/badge primitives this spec touches are codified in §3 (Primitives). The new `.ccx-totals--output` class is a variant of the existing `.ccx-totals` rule — falls under the §3 composition rules for the totals block. No new design-system primitive is introduced; this spec adds one CSS modifier class and a small SPEC.md sub-section codifying the V2 anatomy.

### 3.1 — Header line gains total tokens + total cost

[src/dual_research/ui/static/run-detail.jsx:2982-2995](src/dual_research/ui/static/run-detail.jsx:2982). Restructure the `<header class="ccx-header">` so the sequence becomes:

```jsx
<header className="ccx-header">
  <span className="hd-id">
    <span className={`ccx-icon ${iconClass}`}>{meta.name[0]}</span>
    <span className="nm">{meta.name}</span>
  </span>
  <span className="hd-totals">
    <span className="num">{fmt.tokens(totalTok)}t</span>
    <span className="sep">·</span>
    <span className="num">{fmtCost1(cost)}</span>
  </span>
  <span className="stats">
    ({pctOfCap.toFixed(1)}% of {_fmtCapLabel(ctxWindow)})
  </span>
  <span className="chev" tabIndex={0} role="button" aria-expanded={expanded}
        aria-label={expanded ? 'Collapse' : 'Expand'}
        style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
    <span className="ms ms-20">expand_more</span>
  </span>
</header>
```

The new `.hd-totals` slot sits between `.hd-id` and `.stats`. Per Issue 12 §3 ("data points should start aligning at the same level where the bar starts"): the column-grid for the header must align the totals + percentage at the right edge of the bar-fill column below. CSS-side, add `.hd-totals` and adjust the existing `.ccx-header` grid to a four-column layout.

### 3.2 — Replace the combined Total-tokens bar with two stacked bars

[src/dual_research/ui/static/run-detail.jsx:2999-3014](src/dual_research/ui/static/run-detail.jsx:2999). Delete the single `.ccx-bar-row.is-total` and replace with two bar rows, both above the `{expanded && ...}` gate so they render in both collapsed and unfolded states (architectural decision: render once, used by both states — keeps the "input bar at the top of the unfolded body" invariant from Issue 13 without state-divergence):

```jsx
{/* Spec 0180 §3.2 — total INPUT bar (collapsed + unfolded) */}
<div className="ccx-bar-row ccx-bar-row--total-input">
  <span className="lbl">Total input</span>
  <div className="ccx-bar">
    <div className={`fl ${fillIn}`} style={{ width: `${inputPct}%` }} />
    {reuse.hasReuse && (
      <div className="reuse" style={{ left: 0, width: `${reusePct}%` }} />
    )}
  </div>
  <span className="num">{fmt.tokens(tokensIn)}t &middot; {fmtCost1(inputCost)}</span>
</div>

{/* Spec 0180 §3.2 — total OUTPUT bar (collapsed + unfolded) */}
<div className="ccx-bar-row ccx-bar-row--total-output">
  <span className="lbl">Total output</span>
  <div className="ccx-bar">
    <div className={`fl ${fillOut}`} style={{ width: `${outputPct}%` }} />
  </div>
  <span className="num">{fmt.tokens(tokensOut)}t &middot; {fmtCost1(outCostUsd)}</span>
</div>
```

`inputPct` = `(tokensIn / ctxWindow) * 100`. `outputPct` = `(tokensOut / ctxWindow) * 100` — same scale-base as the input bar so the two bars share a denominator and the visual comparison is meaningful. The reuse-stripe overlay continues to apply only on the input bar (cache reuse is an input-side phenomenon).

CSS: lift the inline grid styling into the `.ccx-bar-row` class itself; both `.ccx-bar-row--total-input` and `.ccx-bar-row--total-output` modifiers inherit the grid from the base class. Add the two modifier rules to both `src/dual_research/ui/static/components.css` and `design-system/assets/styles/composed-components.css` in the same commit.

### 3.3 — Drop the collapsed mono cache-reuse line

[src/dual_research/ui/static/run-detail.jsx:3017-3025](src/dual_research/ui/static/run-detail.jsx:3017). Delete the `{reuse.hasReuse && (<div class="mono">…)}` block. The cache-reuse signal moves into the new output totals block (§3.6) where Issue 13 places it.

### 3.4 — Reorder the unfolded body: input bar already at top, input totals BEFORE output bar

[src/dual_research/ui/static/run-detail.jsx:3028-3098](src/dual_research/ui/static/run-detail.jsx:3028). The new sequence inside the `{expanded && (<React.Fragment>...)}` body becomes:

1. *(input bar already rendered above the expanded gate per §3.2 — no JSX inside the expanded block for it)*
2. Per-input rows — `{grouped.rows.map(renderInputRow)}` (unchanged, [run-detail.jsx:3035](src/dual_research/ui/static/run-detail.jsx:3035)).
3. First divider (unchanged).
4. **Input totals block** (now strictly input — cache-savings removed, see §3.6) — see §3.5.
5. *(output bar already rendered above the expanded gate per §3.2 — no JSX inside the expanded block for it either)*
6. Per-output sub-rows — the `Reasoning` / `Response` / `Tool calls` rows from the existing IIFE at [run-detail.jsx:3078-3098](src/dual_research/ui/static/run-detail.jsx:3078). The IIFE's `outputHeader` variable becomes obsolete (the output header bar moved above the expanded gate); keep only the sub-row rendering logic.
7. Second divider (new) — `<div className="ccx-divider" />` after the per-output rows.
8. **Output totals block** (new) — see §3.6.

### 3.5 — Input totals block — strip cache-savings, keep input-only data

[src/dual_research/ui/static/run-detail.jsx:3103-3145](src/dual_research/ui/static/run-detail.jsx:3103). Modify the existing `<div class="ccx-totals">` so its content becomes input-only:

```jsx
<div className="ccx-totals">
  <div className="line">
    <span className="l">input tokens &middot; billed</span>
    <span className="v">{tokensIn.toLocaleString()}</span>
  </div>
  <div className="line">
    <span className="l">input cost</span>
    <span className="v">{fmtCost1(inputCost)}</span>
  </div>
  {hasSearches && (
    <div className="line">
      <span className="l">
        web search &middot; {queries || searches}{' '}
        {(queries || searches) === 1 ? 'query' : 'queries'}
      </span>
      <span className="v">{fmtCost1(searchCost)}</span>
    </div>
  )}
  <div className="line is-grand">
    <span className="l">total input</span>
    <span className="v">{fmtCost1(inputCost + searchCost)}</span>
  </div>
</div>
```

The cache-savings IIFE at lines 3125-3140 is **removed** from this block.

### 3.6 — Output totals block — new, mirror of §3.5 with cache-savings + reuse

After the second divider (§3.4 step 7), render the new output totals block:

```jsx
<div className="ccx-totals ccx-totals--output">
  <div className="line">
    <span className="l">output tokens</span>
    <span className="v">{tokensOut.toLocaleString()}</span>
  </div>
  <div className="line">
    <span className="l">output cost</span>
    <span className="v">{fmtCost1(outCostUsd)}</span>
  </div>
  {hasOutputSearches && (
    <div className="line">
      <span className="l">
        web search &middot; {outputQueries || outputSearches}{' '}
        {(outputQueries || outputSearches) === 1 ? 'query' : 'queries'}
      </span>
      <span className="v">{fmtCost1(outputSearchCost)}</span>
    </div>
  )}
  {(() => {
    const cacheReadTokens = Number(usage?.cacheRead ?? usage?.cache_read ?? 0) || 0;
    const cacheSavingsUsd = Number(usage?.cacheSavingsUsd ?? usage?.cache_savings_usd ?? 0) || 0;
    if (!(cacheReadTokens > 0 && cacheSavingsUsd > 0)) return null;
    const billed = tokensIn > 0 ? tokensIn : 1;
    const multiplier = cacheReadTokens / billed;
    return (
      <div className="line">
        <span className="l">
          cache savings &middot; &times;{multiplier.toFixed(1)} reuse on{' '}
          {(cacheReadTokens / 1000).toFixed(1)}kt
        </span>
        <span className="v">{fmtCost1(cacheSavingsUsd)}</span>
      </div>
    );
  })()}
  <div className="line is-grand">
    <span className="l">total output</span>
    <span className="v">{fmtCost1(outCostUsd + (outputSearchCost || 0))}</span>
  </div>
</div>
```

**Open data question.** The current code carries `hasSearches` / `queries` / `searches` / `searchCost` as a single set — it does not distinguish input-side web searches from output-side. Per Issue 13 the web-search cost surfaces in **both** totals blocks (input and output) when applicable. The implementer must verify against the wire format:

- If the wire format already separates `web_search_input_*` from `web_search_output_*` fields on `usage`, plumb both into separate locals and feed each into the matching totals block.
- If the wire format only carries a single set (the current assumption), Issue 13's "web searches in output totals" is interpreted as repeating the same `hasSearches` / `searchCost` on the output side (most web-search engagements are output-side anyway — the agent decided to call the tool). Carry both interpretations to the implementer and let them confirm against `usage` shape at branch-cut.

The `outputSearchCost` placeholder above is the variable name to wire once the data path is confirmed.

CSS: add `.ccx-totals--output` to both `src/dual_research/ui/static/components.css` and `design-system/assets/styles/composed-components.css`. The modifier inherits everything from `.ccx-totals`; any per-side tone tweaks (e.g. a subtle warning tint when cache reuse is unusually low) belong in a follow-up DS spec, not here.

### 3.7 — Inline-style hygiene

Lift the repeated inline `style={{ display: 'grid', gridTemplateColumns: 'minmax(140px, 28%) 1fr minmax(110px, max-content)', alignItems: 'center', gap: 10 }}` blobs at [run-detail.jsx:2999-3003](src/dual_research/ui/static/run-detail.jsx:2999) and [run-detail.jsx:3055-3060](src/dual_research/ui/static/run-detail.jsx:3055) onto the existing `.ccx-bar-row` class rule. Verify by reading the current `.ccx-bar-row` CSS rule in [src/dual_research/ui/static/components.css](src/dual_research/ui/static/components.css); if the class already declares the grid (it should — the inline overrides look like accidental duplication from spec 0118's redesign), drop the inline `style={...}` blobs entirely. If the class is missing the grid declaration, lift it up so the inline becomes redundant.

Same lift for the sub-row rendering inside the `SubInputRow` component used by §3.4 step 6 — verify by reading [src/dual_research/ui/static/run-detail.jsx:2762-2810](src/dual_research/ui/static/run-detail.jsx:2762) (the `SubInputRow` definition).

### 3.8 — Codify the V2 anatomy in `design-system/SPEC.md`

Find the Consumption pane sub-section under §4 (verify exact section number at branch-cut — likely §4.something between §4.5 Agent input panel and §4.7 Sources segment). Add or replace a sub-section codifying the V2 anatomy:

> **Consumption card — V2 anatomy.** Per Issues 12 and 13 in `notion-issues/ISSUES.md`. Header (icon · name · total tokens · total cost · `(% of context)` · chevron). Always-visible body: **two stacked bars** — total input bar, total output bar — sharing the same context-window denominator so visual comparison is meaningful. Unfolded body extends with: per-input rows (one per recorded input piece) → divider → input totals text block (input tokens · input cost · web search [when applicable] · total input) → per-output sub-rows (Reasoning · Response · Tool calls when split data exists) → divider → output totals text block (output tokens · output cost · web search [when applicable] · cache savings · total output). The cache-savings reuse-multiplier signal lives in the **output** totals block, not the input side. Inline `style={{...}}` declarations on bar rows are forbidden — all grid + spacing tokens come from the `.ccx-bar-row` class.

Also re-render any Consumption card example in `design-system/assets/Design System v2.html` so the canonical sample reflects the V2 anatomy. Find the example section (search for "ccx-card" or "Consumption" in the HTML); update both the collapsed and unfolded HTML so the visible reference matches the running app.

### 3.9 — Net diff summary

- **`src/dual_research/ui/static/run-detail.jsx`** — ~150 LOC net (add two bar rows at §3.2, drop collapsed mono cache-line at §3.3, restructure unfolded body at §3.4, modify input totals at §3.5, add output totals at §3.6, drop inline styles at §3.7).
- **`src/dual_research/ui/static/components.css`** — add `.ccx-bar-row--total-input`, `.ccx-bar-row--total-output`, `.ccx-totals--output`, `.hd-totals`. Lift inline grid styling onto `.ccx-bar-row` if missing. ~30-50 LOC.
- **`design-system/assets/styles/composed-components.css`** — mirror the CSS changes in §3 (CLAUDE.md two-place rule).
- **`design-system/SPEC.md`** — add the V2 anatomy sub-section per §3.8. ~10 lines of prose.
- **`design-system/assets/Design System v2.html`** — re-render the Consumption card example. ~30-50 lines of HTML.
- **New test file:** `tests/test_consumption_card_v2.py` — see §4.

No new component is introduced; no new primitive lands. No wire-format / backend changes. No event-stream changes. No CHANGELOG fan-out beyond the one PATCH entry.

## 4. Regression-prevention test

Source-level pytest matching the [tests/test_ui_jsx_syntax.py](tests/test_ui_jsx_syntax.py) pattern. New file `tests/test_consumption_card_v2.py`:

```python
"""Spec 0180 — Consumption card V2 anatomy invariants.

The V2 anatomy splits the single combined `Total tokens` bar into two
stacked bars (total-input + total-output) and adds a parallel output
totals block. Cache-savings moves from the input totals to the output
totals. This test locks the structural changes so a defensive add-back
of the combined bar or the mislocated cache line gets caught.
"""
import re
from pathlib import Path

JSX = Path(__file__).parent.parent / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"


def _read():
    return JSX.read_text()


def test_no_combined_total_tokens_bar():
    text = _read()
    # The is-total combined bar from spec 0118 was the V1 anatomy.
    # V2 replaces it with --total-input + --total-output modifiers.
    assert "ccx-bar-row is-total" not in text and "is-total" not in text, (
        "ccx-bar-row.is-total reintroduces the V1 combined Total tokens bar — "
        "spec 0180 §3.2 replaced it with two stacked bars (--total-input + "
        "--total-output). If the combined bar is needed for a different reason, "
        "modify this test and name the spec that justifies it."
    )


def test_total_input_bar_present():
    text = _read()
    assert "ccx-bar-row--total-input" in text, (
        "Spec 0180 §3.2 requires the total-input bar (ccx-bar-row--total-input "
        "modifier) above the expanded gate so it's visible in collapsed state."
    )


def test_total_output_bar_present():
    text = _read()
    assert "ccx-bar-row--total-output" in text, (
        "Spec 0180 §3.2 requires the total-output bar (ccx-bar-row--total-output "
        "modifier) above the expanded gate so it's visible in collapsed state."
    )


def test_output_totals_block_present():
    text = _read()
    assert "ccx-totals--output" in text, (
        "Spec 0180 §3.6 requires the new output totals block "
        "(ccx-totals--output modifier). Without it, the V2 anatomy is "
        "asymmetric — input has totals, output doesn't."
    )


def test_cache_savings_in_output_totals_not_input():
    text = _read()
    # The cache-savings line must land inside the ccx-totals--output block,
    # not the input-only ccx-totals block. We assert: the substring
    # "cache savings" appears AFTER the first "ccx-totals--output" anchor.
    out_anchor = text.find("ccx-totals--output")
    cache_anchor = text.find("cache savings")
    assert out_anchor > 0, "ccx-totals--output anchor missing"
    assert cache_anchor > 0, "cache savings line missing entirely"
    assert cache_anchor > out_anchor, (
        "cache savings line must render inside ccx-totals--output (output totals "
        "block), not the input totals block. Spec 0180 §3.5/§3.6 moves it."
    )


def test_no_inline_grid_on_ccx_bar_row():
    text = _read()
    # The repeated inline grid styling at lines 2999-3003 and 3055-3060 is
    # forbidden by spec 0180 §3.7 — DS hygiene wants grid declarations
    # on the .ccx-bar-row class only.
    pattern = re.compile(
        r"<div\s+className=[\"`]ccx-bar-row[^\"`]*[\"`]\s+[^>]*style=\{\{[^}]*gridTemplateColumns",
        re.DOTALL,
    )
    matches = pattern.findall(text)
    assert not matches, (
        f"Found {len(matches)} ccx-bar-row JSX element(s) carrying an inline "
        f"gridTemplateColumns style — spec 0180 §3.7 forbids this. Move grid "
        f"declarations onto the .ccx-bar-row CSS class."
    )
```

**Before-fix behaviour.** All six tests fail — the JSX currently contains `is-total`, lacks the new modifiers, has the cache-savings line inside the input totals block, and carries inline grid styling.

**After-fix behaviour.** All six tests pass.

- [ ] Test: `tests/test_consumption_card_v2.py::test_no_combined_total_tokens_bar` — locks §3.2 deletion.
- [ ] Test: `tests/test_consumption_card_v2.py::test_total_input_bar_present` — locks §3.2 input bar.
- [ ] Test: `tests/test_consumption_card_v2.py::test_total_output_bar_present` — locks §3.2 output bar.
- [ ] Test: `tests/test_consumption_card_v2.py::test_output_totals_block_present` — locks §3.6 addition.
- [ ] Test: `tests/test_consumption_card_v2.py::test_cache_savings_in_output_totals_not_input` — locks §3.5/§3.6 move.
- [ ] Test: `tests/test_consumption_card_v2.py::test_no_inline_grid_on_ccx_bar_row` — locks §3.7 hygiene.

## 5. Blast radius

- **Files touched.** `src/dual_research/ui/static/run-detail.jsx` (CcxCard, lines 2849-3148), `src/dual_research/ui/static/components.css` (`.ccx-*` block), `design-system/assets/styles/composed-components.css` (mirror), `design-system/SPEC.md` (one sub-section added), `design-system/assets/Design System v2.html` (Consumption card example re-render), `tests/test_consumption_card_v2.py` (new). Six files, one of which is new.
- **Consumers of `CcxCard`.** Search for `<CcxCard` in `run-detail.jsx` — there is exactly one render site, inside the Consumption tab's per-phase grid layout. No other component embeds `CcxCard`. No other tab / panel renders Consumption-card-shaped surfaces.
- **Wire format / data.** No schema or API change. The render reads existing fields off `usage`: `tokensIn`, `tokensOut`, `inputCost`, `outCostUsd`, `searches`, `queries`, `searchCost`, `cacheRead` / `cache_read`, `cacheSavingsUsd` / `cache_savings_usd`, `outputBreakdown.reasoning` / `.response` / `.tool_calls`. All of these are already plumbed. The §3.6 web-search-on-output-side question (does the wire carry `output_search_*` separately?) is the only data-side unknown; resolution at branch-cut per §3.6's "Open data question."
- **No data-layer fan-out.** No aggregator change. No event-stream change. No backend reader change.
- **No tab-level structure change.** The Consumption tab's outer pane chrome (`.ccx-pane`, `.ccx-pane__body`, the per-phase grouping, the legend at the bottom) is untouched. This spec ends at the per-card boundary.
- **CSS hygiene side-effects.** The inline-style cleanup at §3.7 might surface latent CSS bugs (e.g. if the `.ccx-bar-row` class was missing a grid declaration and the inline-style was masking the gap). Mitigation: lift the styling carefully — read the class rule first, only drop the inline if the class already declares the same property. Visual verification against the V2 reference screenshots is the safety net.
- **0148 cache-savings — partial supersession.** Spec 0148 D12 placed the cache-savings line inside the input totals. This spec moves it to the output totals — superseding that specific placement decision while preserving the rendering logic (the same IIFE, just relocated). The user-visible cache-savings copy and the underlying math are unchanged.

## 6. Out of scope

- **Issue 14** — Consumption cards changing horizontal size between phases ("cards in negotiation rounds change format from Phase 0/1 cards"). Separate bug spec — affects the per-phase grid layout, not the card anatomy. The "anatomy is the same across phases" verification step in §7 below confirms that THIS spec does not regress Issue 14, but does not attempt to fix it either.
- **Issue 15** — Sticky legend at the bottom of the Consumption tab. Separate bug spec — affects the tab's outer pane chrome, not the per-card anatomy.
- **Reuse stripe visual on individual input rows.** Issue 13 mentions: "If there is a way how you could also visualise in this individual entries where reuse happened, that would be nice. I guess that's what you already do with the striped visualisation." The striped reuse overlay already exists on the total-input bar (§3.2 preserves it); per-input-row reuse stripes would require per-piece cache-read data which the wire does not split today. Defer to a separate spec if the data path lands.
- **A CI screenshot-diff rig for the consumption card** comparing the live render against `13-unfolded-consumption.png`. Verification at §7 is human-enforced at PR-review time; an automated visual-regression rig is a multi-spec lift outside scope.
- **Bug 1** (Agent Input split-pane) — spec 0171.
- **Bug 2** (critique-card ID chip + `**`) — spec 0172.
- **Bug 3** (three-section input panel one-click reveal) — spec 0178.
- **Bug 4** (critique-card body redundancies + parity verification) — spec 0179.
- **Bug 6** (All-Runs stale `running`) — to be queued separately.

## 7. Risks

- **The wire format does not split web-search cost into input-side vs output-side.** If `usage.searches` / `usage.searchCost` is a single combined number, the §3.6 output totals block can either: (a) duplicate the same line on both input and output side (visually consistent but accounting-inaccurate), or (b) render the web-search line only in the output totals block (most web-search engagements are output-side, but loses input-side visibility). Mitigation: implementer reads `usage` shape at branch-cut and picks (a) or (b) explicitly; document the choice in the handoff. The test in §4 does not gate this decision.
- **Visual-rhythm regression on cards where output is 0 tokens.** If a card has `tokensOut === 0` (rare — early Phase 0 brief cards may not produce output yet?), the new total-output bar renders empty + zero. Mitigation: the bar still renders with the label and the right-side `0t · $0.00` stat — consistent with how the empty input bar would render. If the user feedback flags "empty output bar looks weird on Phase 0 brief", a follow-up spec adds a `{tokensOut > 0 && (<output bar>)}` guard. Out of scope here unless reproducible.
- **CSS lift introduces a layout regression because the inline-style was actually overriding the class.** If `.ccx-bar-row` does NOT currently declare `display: grid; gridTemplateColumns: …` and the inline-style was the only thing making the bars line up, dropping the inline-style without lifting the declaration would collapse the bars. Mitigation: §3.7 explicit instruction to verify the class rule first; if missing, lift up; only THEN drop the inline. The regression test in §4 (`test_no_inline_grid_on_ccx_bar_row`) only locks the JSX side — visual verification at §verify is the layout safety net.
- **The cache-savings line currently surfaces on cards where the user has come to expect it on the input side.** Moving it to the output side is the V2-canonical placement, but anyone who has trained their eye to look for "cache savings" near "input cost" will be surprised. Mitigation: the spec's verification ritual includes a screenshot grid showing the new placement — the change is intentional and documented; the SPEC.md sub-section per §3.8 codifies the new location.
- **CHANGELOG entry must call out the cache-savings relocation explicitly.** The line is moving, not disappearing — phrase the CHANGELOG entry as `### Changed → consumption card: cache-savings line moves from input totals to output totals (Issue 13)`. Anyone scanning the CHANGELOG without reading the spec needs to find that line without effort.
- **Verification screenshots required in the PR description.** Per CLAUDE.md's UI-spec rendered-output rule + per Bug 5's Notion mandate. Eight captures: collapsed + unfolded for one Phase 0 + one Phase 2 + one Phase 4 card (six pairs total — pick a card per phase × per agent if relevant). The verification ritual also explicitly cross-checks Issue 14 (cards don't change format between phases) — verify visually that this spec doesn't introduce a width difference between phases.
