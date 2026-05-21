---
spec: 0146
title: Consumption card visual rework — CcxCard M3 polish + spec-preview rendering
label: new-feature
version-bump: MINOR
status: ready
target-version: 1.12.0
created: 2026-05-21
pr: ""
---

# Spec 0146 — Consumption card visual rework, CcxCard M3 polish, and spec-preview rendering

> Ship bucket: **Consumption tab — finish the M3 anatomy started in 0100/0118, surface the per-attachment token shape from 0145, and unblock the per-piece sub-row token display by fixing the wire-shape camelCase bug.**
> Depends on:
> - **0143** (cost / token data correctness + run-detail header polish — the consumption card now consumes the corrected `usage.cost`, `usage.tokenCost`, `usage.searchCost`, `usage.searches`, `usage.searchQueries` produced by 0143; this spec is the visual layer that surfaces those numbers cleanly).
> - **0145** (canonical prompt-pieces emit + per-attachment token tracking — `groupPiecesForPhase`, `userPromptRowBreakdown`, and the `SubInputRow` primitive all shipped in 0145; this spec consumes them).
> - **0127** (design-system v2 canonicalisation — every CSS token cited below is sourced from `src/dual_research/ui/static/tokens.css`, the canonical M3 token list 0127 froze).
> - **0100** (the original `ccx` card family — anatomy block, sub-row grid, totals block, sticky legend; all of this work edits within that family rather than replacing it).
> Complexity: **M** — one component rewrite (`CcxCard`) plus four scoped CSS blocks plus one server-side 1-line fix (skip dotted keys in `_to_camel`). No protocol or contract churn.
> Targeted version bump: **MINOR (1.11.x → 1.12.0)** — visible Consumption-tab anatomy changes (header trio collapsed to a single percentage, capital-T labels, label-left / value-right totals block, one-decimal costs inside the card, per-attachment rows that now render real token counts after the wire-shape fix). No behaviour contract change.
>
> **Re-validation against current main (commit 63d0277)**: this spec was drafted 2026-05-21 at commit c882e17 before 0143/0144/0145 shipped. Material shifts since:
> - 0143's post-merge backfill rewrote the anchor run's metrics under the new pricing version; `total_cost_usd` moved from $10.3127 → $13.5110, `total_search_cost_usd` from $0.865 → $0.5800, OpenAI cost from $1.8051 → $5.0034. All sanity-check numbers in this spec have been refreshed accordingly.
> - 0145 shipped the per-attachment emitter, `groupPiecesForPhase`, `userPromptRowBreakdown`, and the `SubInputRow` primitive. The original §5.2 plan (`buildSpec0145InputBuckets`, `SPEC_0145_PHASE_PIECES`, `PREVIEW_ATTACHMENTS`, `FILL_CLASS_FOR`) is **dropped** as duplicate work; the §5.3 spec-preview path and the §5.7 round plumbing are **dropped** as obsolete (real data is live).
> - The 0145 handover acknowledged a pre-existing FastAPI `_to_camel` bug that rewrites prompt_pieces dict keys (`user_prompt.message` → `userPrompt.message` on the wire), causing per-piece lookups to miss. This spec adopts the **server-side 1-line fix** (skip dotted keys in `_to_camel`) so per-attachment sub-rows render real token counts instead of `0t`.

---

## 1. Context

The Consumption tab's per-turn card component, `CcxCard` (`src/dual_research/ui/static/run-detail.jsx:2287-2552`, post-0145), has drifted from the design-system §14 reference (`design-system/SPEC.md` §4.3) along five axes that became visible during the anchor-run walkthrough on `20260521-010637-dvs-backend-language-choice` (run-level metrics post-0143 backfill: `total_cost_usd = 13.5110`, `total_search_cost_usd = 0.5800`, Claude `cost_usd = 8.5076` / 20 calls / 2,051,075 input tokens / 130,959 output tokens, OpenAI `cost_usd = 5.0034` / 19 calls / 649,598 input / 50,707 output / 88,448 cache-read).

Looking at the card as it renders today against that run:

1. **The header is overloaded.** Today the header reads `[Claude icon] Claude (8.5% of 1M)` with the percentage sitting right after the name via inline `marginLeft: 'auto'` (run-detail.jsx:2459). The design system specifies a trio (`Xkt total · $cost · X% of cap`); both extremes — the current single-percentage and the spec-reference trio — feel wrong at a glance because the tokens and cost are already to the right of the bar one row down. The right answer (validated during the 0140-batch prototype pass) is a header with just the percentage, but right-aligned to the **bar end** rather than next to the chevron — so the closing `)` of the percentage and the right edge of the bar fill share an x-coordinate. With the current `display: flex` (components.css:2509) the chevron and the percentage compete for the right edge and neither lands cleanly.

2. **Capital-T labels are inconsistent.** Today the collapsed bar reads `Total tokens` (capital T) at `.lbl` (run-detail.jsx:2478) and the output sub-row reads `Output` (capital O), but the design system reference mixes lowercase. This spec back-ports capital-T to the design-system §14 reference so the two sources stay in sync.

3. **No per-attachment surface in the unfolded view by default.** Spec 0145 decomposed `user_prompt` into `user_prompt.message` + `user_prompt.attachment.<id>` at the protocol layer and added a `SubInputRow` primitive plus an expand chevron on the User-prompt row — but the chevron is default-collapsed, so per-attachment rows only appear after a second click on top of the card-unfold click. This spec auto-shows them when the card is unfolded so the marquee surface (per-attachment token attribution) is visible without a second interaction.

4. **Per-piece sub-rows render `0t` because of a wire-shape bug.** [`server.py::_to_camel`](src/dual_research/ui/server.py:1879) recursively camelCases every dict key. Canonical artifact IDs like `user_prompt.message` arrive at the JS as `userPrompt.message`; `prior_turns.phase0` arrives as `priorTurns.phase0`. The current `userPromptRowBreakdown` ([run-detail.jsx:2130](src/dual_research/ui/static/run-detail.jsx)) does snake_case lookups against the wire payload → 0t. The 0145 handover acknowledged this and queued it as a separate follow-up; this spec absorbs the fix (1-line `_to_camel` guard against dotted keys) so the per-attachment surface lands functional.

5. **Totals block does not exist.** Design-system §14 specifies a `.ccx-totals` block (`input billed · input cost · web search · cache savings · total input`). The CSS class is present (components.css:2597-2615) but no JSX site ever instantiates it — the run-detail.jsx render only has the single mono-line "Web search · N queries · $cost" at lines 2540-2547. Costs that the user wants to audit (input vs output vs search) are visible elsewhere in `CostsCluster` (run-detail.jsx:2567+), but the Consumption card itself doesn't have them. Adding `.ccx-totals` to the unfolded state closes the gap and consolidates the audit surface inside the card.

6. **Cost precision is wrong for a glance view.** The card uses the global `fmt.cost(...)` 4-decimal formatter for every cost display (run-detail.jsx:2418, 2486, 2533, 2545). On a 39-call run with per-call costs ranging from `$0.0541` (phase0-r1-claude) to `$0.2324` (phase0-r2-claude), 4-decimal precision creates visual noise and makes the card feel like an audit pane. The Consumption tab is a glance view; the audit surface is the run-detail footer (`$13.5110`) and the reconcile chip. Card-internal costs should be one-decimal (`$0.2`); the footer and reconcile keep 4-decimal.

The rework lands all six at once because they share the same five files (`run-detail.jsx`, `components.css`, `index.html`, `design-system/SPEC.md`, `design-system/assets/styles/composed-components.css`) plus a 1-line server fix, and the same visual cluster. Doing them piecemeal across three minor versions would leave the card visibly inconsistent at every intermediate state.

This spec rewrites the **card-internal** anatomy and the per-attachment surface, and fixes the wire-shape bug that suppressed per-piece token attribution. It does **not** change cost data (0143), the per-attachment emitter (0145), header polish on the run-detail page (0143), or the Compare-tab consumption view (handled by CSS inheritance — same `.ccx` rules flow through, no compare-specific tweaks).

---

## 2. Goals

1. **Single-percentage header, right-aligned to the bar end.** `.ccx-header` becomes a 3-column grid matching the bar-row grid (`minmax(140px, 28%) 1fr minmax(110px, max-content)`, mirrored from the inline bar-row grid at run-detail.jsx:2475), so the `(X.X% of 1M)` percentage sits at column 2 with `justify-self: end` and lands at the same x-coordinate as the right edge of the bar fill below it. The chevron stays at column 3 with `justify-self: end`. Tokens and cost are removed from the header — they live at the right end of the bar (collapsed) or inside the totals block (unfolded).

2. **Capital-T section labels.** `Total tokens` (collapsed) and `Output` (unfolded output sub-row) already use capital T in code (run-detail.jsx:2478, 2522). This spec keeps them and back-ports the capitalisation to design-system §14 in the same PR so the two sources don't drift. The `.ccx-totals` block uses lowercase labels (`input cost`, `total input`) per §5.3 — title case is reserved for bar-row section headers.

3. **Per-attachment sub-rows auto-shown when the card is unfolded.** 0145 added the data path (`userPromptRowBreakdown` + `SubInputRow` + chevron on the User-prompt row); this spec removes the second-click chevron and renders the User-prompt sub-rows (`user_prompt.message` + one `user_prompt.attachment.<id>` per attachment) automatically when the card is in its unfolded state. The chevron-state plumbing is retired; sub-rows always render when the breakdown has content.

4. **Per-piece sub-rows render real token counts.** Fix the camelCase wire-shape bug by adding a 1-line guard in [`server.py::_to_camel`](src/dual_research/ui/server.py:1879): keys containing a dot (canonical artifact IDs) are passed through verbatim instead of being camelCased. After the fix, `user_prompt.message`, `prior_turns.phase0`, `system.task.research_plan` and the like arrive at the JS in the same form the JS expects.

5. **Totals block on the unfolded view.** Below the output row, render `.ccx-totals` with three or four lines (label left, value right, mirroring the bar-row pattern):
   - `input tokens · billed` — raw tabular number (verified: the anchor run's Claude phase0-r2 call has `input_tokens = 52,723`)
   - `input cost` — `fmtCost1(inputCost)` (anchor phase0-r2-claude: `cost_usd = 0.2324` → `$0.2`)
   - `web search · N queries` — `fmtCost1(searchCost)` — only when the call had searches
   - `total input` — `fmtCost1(inputCost + searchCost)` (rendered as `.line.is-grand` — bold rule above, larger value, components.css:2614-2615)

6. **One-decimal cost formatter scoped to the card.** A new `fmtCost1(n)` helper in run-detail.jsx applies to every cost display inside `CcxCard`. The global `fmt.cost(...)` keeps 4-decimal precision for the footer aggregate (`$13.5110`), the reconcile delta column, the per-turn status chips outside the Consumption tab, and tooltip strings.

7. **No regressions on the Compare tab, cross-run views, or the legacy/0118 piece vocabulary.** Pre-0118 runs (legacy 7-key vocabulary at `LEGACY_PIECE_KEYS` in run-detail.jsx:2077) still render via the existing legacy-vocab branch (run-detail.jsx:2342-2345). The attachment surface only renders when `userPromptRowBreakdown` reports `hasAttachments`.

---

## 3. Non-goals

- **No per-attachment emitter work.** Spec 0145 §1 owns the protocol/`pieces_for_*()` decomposition. This spec is the consumer.
- **No cost-data corrections.** Spec 0143 owns the cost/token capture parity work — making sure `usage.cost`, `usage.searchCost`, `usage.searches`, `usage.searchQueries` are accurate end-to-end. This spec reads whatever 0143 ships.
- **No run-detail header polish.** Spec 0143 §3 ships the top-bar copy button + Total cost/token label changes. Card-internal labels are this spec's scope; page-level header chrome stays out.
- **No protocol or contract changes.** No new `usage.*` fields. No new `promptPieces` schema. The `outputBreakdown` / `cacheSavingsUsd` fields proposed in B16 §10 (backend follow-up) are explicitly out of scope; the totals block omits the `cache savings · ×N reuse` line and the output sub-row list stays empty until those fields ship. The `_to_camel` change is an in-scope bug fix to the serialiser, not a contract change — the wire shape of every other dict (non-dotted keys) is unchanged.
- **No canonical prompt-piece vocabulary refresh.** Spec 0145 §3 replaces the legacy UI piece vocabulary (`'system', 'brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'` at run-detail.jsx:2077) with canonical IDs. This spec piggybacks on 0145's helpers (`groupPiecesForPhase`, `userPromptRowBreakdown`, `consumptionLabel`).
- **No spec-preview rendering / synthetic rows.** Previous drafts of this spec included a §5.3 spec-preview path (PREVIEW_ATTACHMENTS, dashed outlines, diagonal stripe, `preview` chip) for the era before 0145's emitter shipped. With 0145 live on main and on production, the spec-preview path is obsolete and removed from scope.
- **No closeout-row rendering.** `closeout.request` row stays suppressed until the aggregator emits `was_closeout: bool` per turn (B16 §10.4, backend follow-up).
- **No Compare-tab visual changes.** Same `CcxCard` flows through to compare; CSS inheritance handles it. No compare-specific rules.
- **No mobile / sub-900 px breakpoint.** Run-detail is desktop-only; the existing grid works down to ~720 px card width.

---

## 4. Current-state audit

### 4.1 — CcxCard JSX (run-detail.jsx)

| Element | File | Lines | Current state |
|---|---|---|---|
| `function CcxCard({ usage, agent, run, scale, expanded, onToggle, tourAnchor, phase })` | [run-detail.jsx:2287-2552](src/dual_research/ui/static/run-detail.jsx) | 2287–2552 | Renders header → total-tokens bar → reuse-signal mono line → (unfolded: divider → per-piece input rows → divider → output row → web-search mono line). No totals block. |
| Header markup | [run-detail.jsx:2456-2469](src/dual_research/ui/static/run-detail.jsx) | 2456–2469 | `<header className="ccx-header">[icon][nm][stats .pct][chev]`. `.stats` has inline `marginLeft: 'auto'` (line 2459); chevron is the rightmost child. The percentage sits next to the chevron, not above the bar end. |
| Total-tokens bar row | [run-detail.jsx:2473-2488](src/dual_research/ui/static/run-detail.jsx) | 2473–2488 | Inline grid `minmax(140px, 28%) 1fr minmax(110px, max-content)`. Label `Total tokens` (capital T). Right text `{fmt.tokens(totalTok)}t · {fmt.cost(cost)}` — 4-decimal cost. |
| Reuse signal mono line | [run-detail.jsx:2491-2499](src/dual_research/ui/static/run-detail.jsx) | 2491–2499 | `9.2kt seen · 246.1kt billed (× 27.0 token reuse) · 11.8kt out` — present on both collapsed and unfolded states when `reuse.hasReuse`. |
| Unfolded input rows | [run-detail.jsx:2502-2509](src/dual_research/ui/static/run-detail.jsx) | 2502–2509 | `grouped.rows.map(renderInputRow)`. `grouped` is from `groupPiecesForPhase(piecesRaw, phase)` (new-vocab branch) or `legacyGroupPieces(piecesRaw)`. Per-attachment sub-rows render via `SubInputRow` when `userPromptExpanded` is true. |
| Output row | [run-detail.jsx:2515-2535](src/dual_research/ui/static/run-detail.jsx) | 2515–2535 | Single `Output` row with `fl.out` / `fl.out-b` bar fill, `fmt.tokens(tokensOut)t · fmt.cost(outCostUsd)` right text. No reasoning / response / tool-calls breakdown. |
| Web-search mono line | [run-detail.jsx:2539-2547](src/dual_research/ui/static/run-detail.jsx) | 2539–2547 | `Web search · N queries · $cost` — present at the bottom of the unfolded section when `hasSearches`. Free-text, not in `.ccx-totals`. |
| `renderInputRow` | [run-detail.jsx:2352-2450](src/dual_research/ui/static/run-detail.jsx) | 2352–2450 | Inline 3-column grid per row. Right text `fmt.tokens(tokens)t · fmt.cost(propCost)` — 4-decimal cost. User-prompt row gets a chevron + `SubInputRow` block when `attachmentBreakdown` is non-null and `userPromptExpanded` is true. |
| `userPromptExpanded` state | [run-detail.jsx:2295](src/dual_research/ui/static/run-detail.jsx) | 2295 | `React.useState(false)` — default-collapsed; the chevron toggles it. This state is retired by §5.2 (sub-rows always render when card is unfolded). |
| `SubInputRow` | [run-detail.jsx:2238-2264](src/dual_research/ui/static/run-detail.jsx) | 2238–2264 | Indented sub-row using `.ccx-bar-row.ccx-bar-row--sub` (BEM modifier). Smaller bar height, dimmed bar fill, faint text. Reused as-is by §5.2. |
| `userPromptRowBreakdown` | [run-detail.jsx:2130-2149](src/dual_research/ui/static/run-detail.jsx) | 2130–2149 | Decomposes piecesRaw into `{ total, message, attachments, hasAttachments, hasMessage }`. Currently does snake_case lookups against the camelCased wire payload — §5.6 fixes the wire so these lookups land. |
| ConsumptionView call site | [run-detail.jsx:2034-2042](src/dual_research/ui/static/run-detail.jsx) | 2034–2042 | Passes `usage, agent, run, scale, phase, expanded, onToggle, tourAnchor`. `phase` is `row.phase` (the phase number 0–4). |

### 4.2 — Consumption CSS (`components.css`)

| Block | File | Lines | Current state |
|---|---|---|---|
| `.ccx` container | [components.css:2502-2508](src/dual_research/ui/static/components.css) | 2502–2508 | `background: var(--md-surface-container); border: 1px solid var(--md-outline-hair); border-radius: var(--md-shape-md); padding: 14px 16px; display: flex; flex-direction: column; gap: 8px;` |
| `.ccx-header` (flex) | [components.css:2509](src/dual_research/ui/static/components.css) | 2509 | `display: flex; align-items: center; gap: 10px; padding-bottom: 4px;` — needs grid conversion. |
| `.ccx-header .stats` | [components.css:2519-2525](src/dual_research/ui/static/components.css) | 2519–2525 | `margin-left: auto; display: inline-flex; gap: 8px; font: var(--md-w-regular) 13px/1 var(--md-font-data); color: var(--md-on-surface-variant);` — `margin-left: auto` doesn't apply under grid; the new rule uses `justify-self: end` (§5.1). |
| `.ccx-bar-row, .ccx-sub-row` grid | [components.css:2540-2548](src/dual_research/ui/static/components.css) | 2540–2548 | `grid-template-columns: 140px 1fr 100px; gap: 12px;` — this is the grid we mirror on the header (§5.1). |
| `.ccx-bar` + agent fills | [components.css:2549-2569](src/dual_research/ui/static/components.css) | 2549–2569 | Bar geometry (`height: 10px; border-radius: var(--md-shape-full); overflow: hidden`) + `.fl.in / .in-b / .out / .out-b / .sys / .hist / .round / .tools / .web / .reason / .resp / .toolc` agent + sub-bucket fills via `var(--p-sable)`, `var(--p-sage)`, `var(--p-info)`. |
| `.ccx-bar .reuse` stripe | [components.css:2570-2582](src/dual_research/ui/static/components.css) | 2570–2582 | Cache-reuse diagonal-stripe overlay. Light + dark variants. |
| `.ccx-totals` block | [components.css:2597-2615](src/dual_research/ui/static/components.css) | 2597–2615 | `display: grid; grid-template-columns: 1fr; gap: 4px; padding: 10px 12px; margin-top: 8px; background: var(--md-surface-container-low); border-radius: var(--md-shape-sm); border: 1px solid var(--md-outline-hair);` — `.line { display: flex; justify-content: space-between; }`. Already has `.is-savings` and `.is-grand` modifiers; we just need to instantiate it in JSX. |
| Sticky bottom legend | [components.css:2638-2676](src/dual_research/ui/static/components.css) | 2638–2676 | Untouched by this spec. |

### 4.3 — M3 tokens in scope (`tokens.css`)

Every CSS value cited in §5 reads from these. Each is verified present in `src/dual_research/ui/static/tokens.css`:

| Token | Line | Used for |
|---|---|---|
| `--md-surface-container` | 171 | `.ccx` card background |
| `--md-surface-container-low` | 170 | `.ccx-totals` block background |
| `--md-surface-container-high` | 172 | Sticky legend (unchanged) |
| `--md-on-surface` | 175 | `.ccx-bar-row.is-total .lbl`, totals `.v` |
| `--md-on-surface-variant` | 176 | `.ccx-bar-row .lbl`, totals base text |
| `--md-on-surface-muted` | 177 | sub-row `.lbl`, sub-row `.num` |
| `--md-on-surface-faint` | 178 | totals `.l`, preview-row tooltip text, reuse-signal mono line |
| `--md-outline-hair` | 183 | `.ccx` border, `.ccx-divider`, totals block border |
| `--md-shape-xs` | 230 | 4px — preview chip outline radius |
| `--md-shape-sm` | 231 | 8px — totals block border-radius |
| `--md-shape-md` | 232 | 12px — `.ccx` card border-radius |
| `--md-shape-full` | 235 | 9999px — bar pill rounding |
| `--md-label-s-size` | 221 | 11px — preview chip text size, totals `.l` |
| `--md-label-m-size` | 220 | 12px — sub-row label |
| `--md-title-s-size` | 213 | 14px — header `.nm` |
| `--md-body-s-size` | 217 | 12px — bar-row label |
| `--md-font-plain` | 198 | sans-serif default |
| `--md-font-data` | 200 | tabular numerics for token / cost displays |
| `--md-w-regular` / `-medium` / `-semi` | 224–226 | font weights (400 / 500 / 600) |
| `--md-sp-2` / `-3` | 240–241 | 8 / 12px spacing |
| `--p-sable` | 131 | Claude agent fill (`.fl.in`) |
| `--p-sage` | 133 | OpenAI agent fill (`.fl.in-b`) |
| `--p-info` | (palette block) | Web / tool-call accent |
| `--p-ok` | (palette block) | Cache-savings text colour (`.line.is-savings .v`) |
| `--agent-a` / `--agent-b` | 10 / 17 | Agent identity for icon backgrounds (mapped via `--md-primary` / `--md-secondary` at 142 / 147) |

The card does NOT use `--dr-card-pad-v` / `--dr-card-pad-h` (those are scoped to `.qthread` / `.tl-card`); `.ccx` uses its own inline `padding: 14px 16px`. This spec keeps that as-is — repointing to `--dr-card-pad-*` is a separate cosmetic that affects every card primitive and belongs to a design-system polish pass, not here.

---

## 5. Proposed change

Six coordinated subsections. Each cites the exact file:line touched and the exact CSS token used.

### 5.1 — Header: 3-column grid, percentage right-aligned to bar end

Convert `.ccx-header` from flex to a grid that matches the bar-row grid below it. The closing `)` of `(X.X% of 1M)` lands at the same x-coordinate as the right edge of the bar fill — verifiable programmatically with `stats.getBoundingClientRect().right === bar.getBoundingClientRect().right`.

**CSS patch** ([components.css:2509-2527](src/dual_research/ui/static/components.css), replacing the existing rules):

```css
.ccx-header {
  display: grid;
  grid-template-columns: minmax(140px, 28%) 1fr minmax(110px, max-content);
  align-items: center;
  gap: 10px;
  padding-bottom: 4px;
}
.ccx-header .hd-id {
  display: inline-flex; align-items: center; gap: 10px;
  min-width: 0; overflow: hidden;
}
.ccx-header .stats {
  justify-self: end;
  white-space: nowrap;
  display: inline-flex; gap: 8px; align-items: baseline;
  font: var(--md-w-regular) var(--md-body-s-size)/1 var(--md-font-data);
  color: var(--md-on-surface-faint);
  font-variant-numeric: tabular-nums;
}
.ccx-header .chev {
  justify-self: end;
  /* (width/height/transition/focus-visible rules unchanged) */
}
```

The inline `marginLeft: 'auto'` on `.stats` is **removed** (flex semantics don't apply under grid). `.stats { white-space: nowrap; }` prevents the percentage from wrapping when cards render side-by-side at 1280 px viewport. The grid template matches the bar-row inline grid at run-detail.jsx:2475 verbatim so the column boundary aligns pixel-exactly.

**JSX patch** ([run-detail.jsx:2456-2469](src/dual_research/ui/static/run-detail.jsx)):

```jsx
<header className="ccx-header">
  <span className="hd-id">
    <span className={`ccx-icon ${iconClass}`}>{meta.name[0]}</span>
    <span className="nm">{meta.name}</span>
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

The `.pct` and `.sep` child spans inside `.stats` ([components.css:2526-2527](src/dual_research/ui/static/components.css)) become unused because `.stats` itself now holds only the bracketed percentage. The two `.pct` / `.sep` rules are left in place — they're harmless.

### 5.2 — Auto-show per-attachment sub-rows when card is unfolded

0145 added the data path: `userPromptRowBreakdown` ([run-detail.jsx:2130-2149](src/dual_research/ui/static/run-detail.jsx)) decomposes piecesRaw into a `{ total, message, attachments, hasAttachments, hasMessage }` shape, and `SubInputRow` ([run-detail.jsx:2238-2264](src/dual_research/ui/static/run-detail.jsx)) renders the indented child row with the `.ccx-bar-row--sub` modifier. The only thing 0145 left collapsed-by-default was the affordance: the User-prompt row gets a `▸` chevron that toggles `userPromptExpanded` state, and sub-rows only render when expanded.

This spec retires the chevron + state pair. When the card is unfolded (`expanded === true`) and `row.attachmentBreakdown` is non-null, the sub-rows render unconditionally. No second click required.

**Changes in `CcxCard` ([run-detail.jsx:2287-2552](src/dual_research/ui/static/run-detail.jsx)):**

- Delete the `userPromptExpanded` state ([run-detail.jsx:2295](src/dual_research/ui/static/run-detail.jsx)).
- Delete the chevron `<span role="button">` block inside `renderInputRow` ([run-detail.jsx:2378-2406](src/dual_research/ui/static/run-detail.jsx)) — the `▸` affordance, its keyboard handlers, and the transform animation.
- Replace the `{isUserPromptExpandable && userPromptExpanded && (...)}` block ([run-detail.jsx:2421-2447](src/dual_research/ui/static/run-detail.jsx)) with `{isUserPromptExpandable && (...)}` — sub-rows render whenever the User-prompt row has an `attachmentBreakdown`.

The existing `consumptionLabel(id)` (artifact registry display-name resolver at [run-detail.jsx:2228-2233](src/dual_research/ui/static/run-detail.jsx)) handles attachment titles via the `Attachment · {title}` template in the registry. The attachment ID — the `<id>` portion of `user_prompt.attachment.<id>` — flows from piecesRaw's keys into the label. When the run's `attachments.json` has a title for the matching ID, `consumptionLabel` resolves to `Attachment · Foo`; otherwise it falls back to the raw ID.

(No new helper functions, no new constants, no PREVIEW_ATTACHMENTS, no FILL_CLASS_FOR. The 0145 helpers — `groupPiecesForPhase`, `userPromptRowBreakdown`, `SubInputRow`, `consumptionLabel` — already cover everything §5.2 needs. The fill class is the same `fillIn` (`in` or `in-b`) that the parent User-prompt row uses; the indent + opacity come from the `.ccx-bar-row--sub` styling.)

### 5.3 — Totals block on the unfolded view

Replace the free-text web-search mono line at [run-detail.jsx:2539-2547](src/dual_research/ui/static/run-detail.jsx) with a `.ccx-totals` block, rendered after the output row.

**JSX patch** (replaces the existing `hasSearches` mono div):

```jsx
<div className="ccx-totals">
  <div className="line">
    <span className="l">input tokens · billed</span>
    <span className="v">{tokensIn.toLocaleString()}</span>
  </div>
  <div className="line">
    <span className="l">input cost</span>
    <span className="v">{fmtCost1(inputCost)}</span>
  </div>
  {hasSearches && (
    <div className="line">
      <span className="l">web search · {queries || searches} {(queries || searches) === 1 ? 'query' : 'queries'}</span>
      <span className="v">{fmtCost1(searchCost)}</span>
    </div>
  )}
  <div className="line is-grand">
    <span className="l">total input</span>
    <span className="v">{fmtCost1(inputCost + searchCost)}</span>
  </div>
</div>
```

The existing `.ccx-totals .line` rule already has `display: flex; align-items: baseline; justify-content: space-between;` at [components.css:2606-2607](src/dual_research/ui/static/components.css), so labels-left / values-right is automatic — the DOM child order is `.l` then `.v` and the flex direction does the rest. The `.is-grand` modifier at [components.css:2614-2615](src/dual_research/ui/static/components.css) gives the bold rule above + larger `.v` font.

**Anchor-run sanity check** (phase0-r2-claude call: `cost_usd = 0.232364`, `search_cost = 0.02`, `input_tokens = 52,723`, `output_tokens = 3,613`):
- `input tokens · billed` → `52,723`
- `input cost` → `$0.2` (after subtracting output cost; `inputCost = tokenCost - outCostUsd` per existing `CcxCard` logic at run-detail.jsx:2322)
- `web search · 2 queries` → `$0.0` (`fmtCost1(0.02)` = `$0.0`; see §5.4 trade-off)
- `total input` → `$0.2`

The `cache savings · ×N reuse on Xk` line from design-system §14 is **omitted** until backend ships `usage.cacheSavingsUsd` (B16 §10.2, out-of-scope for this spec).

### 5.4 — `fmtCost1` helper + scoped application

New helper appended to the existing formatter block in `run-detail.jsx` (near `fmt.cost` definition):

```javascript
// Spec 0146: one-decimal cost formatter, scoped to the Consumption card.
// `fmt.cost` keeps 4-decimal precision for the audit surfaces (footer,
// reconcile, status chips, tooltips).
function fmtCost1(n) {
  const v = Number(n) || 0;
  return `$${v.toFixed(1)}`;
}
```

Applied **only inside `CcxCard`** to:
- Total-tokens bar right text ([run-detail.jsx:2486](src/dual_research/ui/static/run-detail.jsx))
- Per-input-row right text (inside `renderInputRow` at [run-detail.jsx:2418](src/dual_research/ui/static/run-detail.jsx))
- `SubInputRow` right text ([run-detail.jsx:2260](src/dual_research/ui/static/run-detail.jsx))
- Output-row right text ([run-detail.jsx:2533](src/dual_research/ui/static/run-detail.jsx))
- Every totals-block `.v` (§5.3)

The global `fmt.cost(...)` keeps 4-decimal precision and is unchanged for:
- Run-detail footer aggregate (`$13.5110` — verified against the anchor run's `total_cost_usd`)
- Reconcile delta column
- Per-turn status chips outside the Consumption tab
- Tooltip strings

**Sub-cent cost trade-off.** `fmtCost1(0.02)` → `$0.0`, which reads as "free" on cards that ran one search. The anchor run has `total_search_cost_usd = 0.5800` and 14 of 39 calls had `search_cost > 0` — at one-decimal precision most per-call search costs render as `$0.0` or `$0.1`. The default for this spec is to keep `$0.0`; if user-testing flags the "free" misread, a `<$0.1` representation for non-zero sub-5¢ amounts is a one-line follow-up. See §10 open question.

### 5.5 — `index.html` cache-buster bump

Bump the `?v=` query parameter on every CSS + JSX import in [index.html](src/dual_research/ui/static/index.html) from `?v=0145a` → `?v=0146a`. Mechanical, ~40 lines.

### 5.6 — Server fix: `_to_camel` skips dotted keys

[`server.py::_to_camel`](src/dual_research/ui/server.py:1879) currently camelCases every dict key recursively. Canonical artifact IDs like `user_prompt.message` arrive at the JS as `userPrompt.message`; the camelCasing fights every JS lookup that uses the canonical (Python-source-of-truth) string.

**Patch** (1 line guard inside the existing dict branch):

```python
def _to_camel(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str):
                # Spec 0146 — canonical artifact IDs (dotted strings such as
                # "user_prompt.message" or "prior_turns.phase0") are the
                # Python source of truth; pass them through verbatim so
                # JS lookups can use the same key shape both sides.
                if "." in k:
                    out[k] = _to_camel(v)
                else:
                    out[_snake_to_camel(k)] = _to_camel(v)
            else:
                out[str(k)] = _to_camel(v)
        return out
    ...
```

The guard is keyed on `.` because every multi-segment canonical artifact ID is dotted (every Python field name in `dataclass` / `dict` shape is single-segment snake_case — `phase_timings`, `started_at`, `input_tokens` — none has a dot). The behaviour for every other consumer is unchanged.

**Single-segment canonical IDs.** Three legacy canonical IDs are single-segment snake_case without a dot: `user_prompt` (legacy aggregate), `current_draft`, `all_p2_turns`. The dot-guard above doesn't catch them — they still arrive at the JS as `userPrompt` / `currentDraft` / `allP2Turns`. Handling these on the server would require enumerating the registry inside `_to_camel`; cleaner to inverse the transform on the JS side with a 6-line `normalisePiecesRaw` helper in `run-detail.jsx` that adds the snake_case alias for any camelCased key it sees:

```javascript
function normalisePiecesRaw(piecesRaw) {
  if (!piecesRaw || typeof piecesRaw !== 'object') return piecesRaw;
  const out = {};
  for (const [k, v] of Object.entries(piecesRaw)) {
    out[k] = v;
    if (typeof k === 'string' && /[A-Z]/.test(k)) {
      const snake = k.replace(/([A-Z])/g, '_$1').toLowerCase();
      if (!(snake in out)) out[snake] = v;
    }
  }
  return out;
}
```

`CcxCard` calls `normalisePiecesRaw(usage.promptPieces)` once when computing its local `piecesRaw`; all downstream consumers (`groupPiecesForPhase`, `userPromptRowBreakdown`, every `piecesRaw[k]` lookup) see both the wire form and the canonical snake_case form.

**Regression coverage:** add a new test that feeds `{"user_prompt.message": 100, "prior_turns.phase0": 50, "phase_timings": {...}, "started_at": "..."}` through `_to_camel` and asserts the dotted keys are preserved while the snake_case fields are camelCased.

### 5.7 — Design-system back-port

Four updates to `design-system/SPEC.md` §4.3 + the example HTML (`design-system/assets/Design System v2.html` §14) + `design-system/assets/styles/composed-components.css`, all in this PR:

1. **Header trio collapses to single percentage**, right-aligned to bar end. Document the `(X.X% of 1M)` placement at column 2 with `justify-self: end`.
2. **Capital-T labels** on bar-row section headers (`Total tokens`, `Output`); totals-block lines stay lowercase (`input cost`, `total input`).
3. **Totals block labels left, values right** (current reference HTML inverts; back-port the swap).
4. **One-decimal cost displays** inside the card; document the `fmtCost1` scope and the `$0.0` / `<$0.1` trade-off.

`design-system/CHANGELOG.md` gets one entry pointing at spec 0146.

`design-system/assets/styles/composed-components.css` mirrors the `.ccx-header` grid changes from §5.1 verbatim.

---

## 6. Out of scope

Restated as a backstop against scope creep during implementation:

- **No protocol or emitter changes.** Spec 0145 owns `pieces_for_*()` decomposition.
- **No cost-data correction.** Spec 0143 owns the `usage.*` parity work; this spec consumes whatever 0143 ships.
- **No header polish on the run-detail page.** Spec 0143 owns the top-bar copy button + Total cost/token label work.
- **No `outputBreakdown` rendering.** Backend follow-up; the output-row stays a single `Output` row until reasoning / response / tool-calls are split (B16 §10.1).
- **No `cacheSavingsUsd` line in the totals block.** Backend follow-up (B16 §10.2).
- **No `closeout.request` row.** Backend follow-up (B16 §10.4).
- **No Compare-tab tweaks.** Same `CcxCard` flows through.
- **No mobile breakpoint.** Run-detail is desktop-only.

---

## 7. Test plan

### 7.1 — Unit (Python + JS parity)

- [ ] `fmtCost1(0.5028) === '$0.5'`
- [ ] `fmtCost1(0.02)   === '$0.0'`
- [ ] `fmtCost1(undefined) === '$0.0'`
- [ ] `fmtCost1(13.5110) === '$13.5'` (anchor `total_cost_usd`)
- [ ] `_to_camel({"user_prompt.message": 100, "started_at": "x"})` returns `{"user_prompt.message": 100, "startedAt": "x"}` — dotted keys preserved, snake_case fields camelCased.
- [ ] `_to_camel({"prior_turns.phase0": 42, "phase_timings": {"r1": 1}})` preserves `"prior_turns.phase0"` and camelCases `phase_timings → phaseTimings`. Nested dict still camelCases its single-segment keys.

### 7.2 — Pixel alignment

- [ ] After the header grid lands, programmatic check: for every `.ccx` on the Consumption tab of the anchor run, `stats.getBoundingClientRect().right === bar.getBoundingClientRect().right` (within 1px).
- [ ] The `(X.X% of 1M)` percentage does not wrap when the run-detail viewport is 1280 px wide (cards rendered side-by-side via `.cards-2up`).

### 7.3 — Visual / integration (manual against deployed UI)

- [ ] Open `/#/runs/20260521-010637-dvs-backend-language-choice` → Consumption tab.
  - [ ] Header reads `[icon][Claude]                         (X.X% of 1M) [chevron]` with the closing `)` directly above the right edge of the bar fill.
  - [ ] Collapsed view shows a single `Total tokens` bar with `Xkt · $X.X` at the right (one-decimal cost).
  - [ ] Cache-reuse stripe is visible on the OpenAI bars (cache_read = 88,448 tokens on this run).
- [ ] Expand the P0-R2-Claude card. Verify:
  - [ ] `Total tokens` (capital T) and `Output` (capital O) are present.
  - [ ] Input sub-rows render via `groupPiecesForPhase` in arrival order — the `User prompt` row resolves through `userPromptRowBreakdown` (legacy-aggregate path until per-attachment data flows in fresh runs).
  - [ ] Totals block: `input tokens · billed   52,723` / `input cost $0.2` / `web search · 2 queries $0.0` / `total input $0.2` (bold rule above).
- [ ] Fire a fresh attachment-bearing run (via `/dual-research-run`) and open its CcxCard at P0/P2/P4:
  - [ ] User-prompt row's sub-rows render automatically when card is unfolded (no second click required).
  - [ ] Each attachment renders as `Attachment · {title}` resolved from the registry.
  - [ ] Per-attachment token counts are non-zero (proves the `_to_camel` fix landed).
- [ ] Light-mode parity: toggle `.light` body class. The totals block reads on cream; bar colours and stripes carry over correctly.
- [ ] Compare tab: open two runs side-by-side. Confirm both Consumption panes render with the same header anatomy and totals block, no compare-specific regressions.

### 7.4 — Visual regression snapshots

- [ ] Capture the Consumption tab at:
  - `/#/runs/20260521-010637-dvs-backend-language-choice` (legacy-shim path; P0–P4 deadlocked; 39 calls; total `$13.5110`)
  - One fresh attachment-bearing run (real attachments exercise the per-attachment surface)
- [ ] Capture light + dark variants.
- [ ] Before/after diff: the only intended deltas are §5.1–§5.5 changes. Anything else flagged is a regression.

### 7.5 — Cache bust

- [ ] After deploy, hard-reload the run-detail page; confirm the new anatomy renders (i.e. the `?v=0146a` cache-bust took effect).

### 7.6 — Backward compatibility

- [ ] Open a pre-0118 run (legacy 7-key vocab; e.g. `LEGACY_PIECE_KEYS = ['brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp']`). The legacy renderer path at [run-detail.jsx:2342-2345](src/dual_research/ui/static/run-detail.jsx) is unchanged — verify the card renders with the legacy labels.
- [ ] Open the anchor run (post-0118, pre-0145; legacy `user_prompt` aggregate via shim). The new renderer path activates; the aggregate routes to the User-prompt row via `userPromptRowBreakdown`'s legacy fallback.

---

## 8. Risks

- **Header overflow at narrow widths.** Cards rendered side-by-side at < 900 px viewport could push the percentage into the chevron column. **Mitigation:** `white-space: nowrap` on `.stats` + verified down to 720 px during the prototype walkthrough. If a narrower viewport ever surfaces wrapping, drop the col-2 `1fr` to `minmax(80px, 1fr)` so the chevron column overflows first.
- **`fmtCost1` reading as "free" on sub-cent costs.** `$0.02` → `$0.0` on cards that ran a single search. On the anchor run, this affects ~14 of 39 calls. **Mitigation:** open question §10.1 keeps `$0.0` as the default; the totals block + run-detail footer carry the audit truth.
- **`_to_camel` change ripples to other consumers.** The guard skips camelCasing for dotted keys; any wire payload that contained dotted snake_case keys before (e.g. a hypothetical `nested.snake_case`) would now preserve the dot-and-underscore form. **Mitigation:** every prod payload checked manually — no other dict has dotted snake_case keys; canonical artifact IDs are the only consumers. Test §7.1 pins both behaviours (dotted preserved, single-segment snake_case still camelCased).
- **CSS-token drift between `components.css` and `composed-components.css`.** Two surfaces, two file paths; the design-system audit workflow doesn't yet diff them in CI. **Mitigation:** §5.7 includes the design-system mirror update in the same PR; the manual diff happens once at review time. A CI-level diff is a follow-up for the design-system audits workflow (not this spec).
- **Visual regression on adjacent consumption views.** Compare tab + Search-palette previews + cross-run hover cards all use the same `.ccx` rules. **Mitigation:** §7.3 manual pass covers the Compare tab; Search-palette and cross-run hover don't render full `CcxCard` (different component path), so they're insulated. Confirm during review.
- **Cache-bust forgotten.** Repeat of every prior visual spec's risk. **Mitigation:** §7.5 makes it explicit; the bump from `?v=0145a` to `?v=0146a` is mechanical (find-replace across 40 lines in `index.html`).
- **Anchor run is attachment-less.** The legacy-shim path renders without exercising the per-attachment surface. **Mitigation:** §7.3 includes a fresh attachment-bearing run firing as part of smoke; the per-attachment row coverage is in §7.1 unit tests against synthetic fixtures.

---

## 9. Files touched (concrete list)

```
src/dual_research/ui/static/run-detail.jsx
  - rewrite CcxCard header markup (≈14 LOC)
  - add fmtCost1 helper (≈6 LOC)
  - retire userPromptExpanded state + chevron + collapse plumbing (-30 LOC)
  - flatten User-prompt sub-row block to always render when card unfolded (≈8 LOC)
  - add .ccx-totals JSX block in the unfolded section (≈22 LOC)
  - swap to fmtCost1 at the cost callsites inside CcxCard + SubInputRow (≈5 LOC)

src/dual_research/ui/static/components.css
  - .ccx-header → grid (≈10 LOC, replaces existing flex)
  - .ccx-header .hd-id new rule (≈4 LOC)
  - .ccx-header .stats { justify-self: end; white-space: nowrap; … } (≈8 LOC, replaces existing flex margin-left:auto)
  - .ccx-header .chev { justify-self: end; … } (1 LOC additive)

src/dual_research/ui/static/index.html
  - bump ?v=0145a → ?v=0146a across all CSS + JSX imports (≈40 LOC, mechanical)

src/dual_research/ui/server.py
  - _to_camel skips dotted keys (≈3 LOC inside the existing if-branch)

tests/ui/test_to_camel.py (new)
  - regression test on dotted-key preservation + single-segment camelCasing

design-system/assets/styles/composed-components.css
  - mirror the .ccx-header grid changes from components.css (matches §5.1)

design-system/SPEC.md
  - rewrite §4.3 "Consumption card" per §5.7

design-system/assets/Design System v2.html
  - rewrite §14 anatomy + examples per §5.7
  - update the consumption HTML mocks for the new collapsed + unfolded look

design-system/CHANGELOG.md
  - new entry for spec 0146

pyproject.toml, src/dual_research/__init__.py, uv.lock
  - 1.11.0 → 1.12.0

CHANGELOG.md
  - [1.12.0] entry
```

One 3-line server fix (the `_to_camel` dotted-key guard), one new test file, and one version bump. No protocol changes, no schema migrations, no contract changes.

---

## 10. Open questions — resolutions

1. **Sub-cent cost display (§5.4).** Keep `$0.0` for non-zero amounts under 5¢. The totals block + run-detail footer carry the audit truth. **Resolved.**

2. **`fmtCost1` scope creep — apply to footer aggregate too?** Keep 4-decimal in the footer; it's the audit number, the card is the glance. **Resolved.**

3. **Capital-T labels.** Apply to bar-row section headers only (`Total tokens`, `Output`). The `.ccx-totals` block uses lowercase labels (`input cost`, `total input`) per §5.3 JSX. Design-system §14 back-port in §5.7 locks both rules in. **Resolved.**

4. **§5.3 spec-preview rendering — still needed?** No. 0145 shipped the per-attachment emitter and the legacy-shim, so the synthetic-row scaffolding (preview chips, diagonal stripes, PREVIEW_ATTACHMENTS, etc.) has nothing to render. §5.3 and §5.7 (round plumbing) are removed from scope. **Resolved.**

5. **Preview-row totals reconciliation.** Moot — no preview rows in this spec. **Resolved.**

### Additional resolutions captured during re-validation against current main

6. **camelCase wire-shape bug.** Adopt a 1-line server fix in `_to_camel` (skip dotted keys) so per-attachment sub-rows render real token counts. Spec §5.6 ships it. **Resolved.**

7. **Per-attachment row visibility.** Auto-show sub-rows when the card is unfolded; retire 0145's `▸` chevron + `userPromptExpanded` state. Spec §5.2 ships it. **Resolved.**
