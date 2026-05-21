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

> Ship bucket: **Consumption tab — finish the M3 anatomy started in 0100/0118, surface the per-attachment token shape from 0145, and render the spec-0145 input list before the emitter side fully lands.**
> Depends on:
> - **0143** (cost / token data correctness + run-detail header polish — the consumption card now consumes the corrected `usage.cost`, `usage.tokenCost`, `usage.searchCost`, `usage.searches`, `usage.searchQueries` produced by 0143; this spec is the visual layer that surfaces those numbers cleanly).
> - **0145** (canonical prompt-pieces emit + per-attachment token tracking — the per-attachment sub-row contract in §5.2 reads the `user_prompt.message` and `user_prompt.attachment.<id>` keys 0145 introduces).
> - **0127** (design-system v2 canonicalisation — every CSS token cited below is sourced from `src/dual_research/ui/static/tokens.css`, the canonical M3 token list 0127 froze).
> - **0100** (the original `ccx` card family — anatomy block, sub-row grid, totals block, sticky legend; all of this work edits within that family rather than replacing it).
> Complexity: **M** — one component rewrite (`CcxCard`) plus four scoped CSS blocks plus a small JS helper (`buildSpec0145InputBuckets`). No backend, no protocol, no contract churn.
> Targeted version bump: **MINOR (1.11.x → 1.12.0)** — visible Consumption-tab anatomy changes (header trio collapsed to a single percentage, capital-T labels, label-left / value-right totals block, one-decimal costs inside the card, per-attachment rows). No behaviour contract change; the data contract widens by reading 0145 keys but degrades gracefully when only the legacy `userPrompt` aggregate is present.

---

## 1. Context

The Consumption tab's per-turn card component, `CcxCard` (`src/dual_research/ui/static/run-detail.jsx:2113-2311`), has drifted from the design-system §14 reference (`design-system/SPEC.md` §4.3) along five axes that became visible during the anchor-run walkthrough on `20260521-010637-dvs-backend-language-choice` (run-level metrics: `total_cost_usd = 10.3127`, `total_search_cost_usd = 0.865`, Claude `cost_usd = 8.5076` / 20 calls / 2,051,075 input tokens / 130,959 output tokens, OpenAI `cost_usd = 1.8051` / 19 calls / 649,598 input / 50,707 output / 88,448 cache-read).

Looking at the card as it renders today against that run:

1. **The header is overloaded.** Today the header reads `[Claude icon] Claude (8.5% of 1M)` with the percentage sitting right after the name via `margin-left: auto` (components.css:2519-2525). The design system specifies a trio (`Xkt total · $cost · X% of cap`); both extremes — the current single-percentage and the spec-reference trio — feel wrong at a glance because the tokens and cost are already to the right of the bar one row down. The right answer (validated during the 0140-batch prototype pass) is a header with just the percentage, but right-aligned to the **bar end** rather than next to the chevron — so the closing `)` of the percentage and the right edge of the bar fill share an x-coordinate. With the current `display: flex` (components.css:2509) the chevron and the percentage compete for the right edge and neither lands cleanly.

2. **Capital-T labels are inconsistent.** Today the collapsed bar reads `Total tokens` (capital T) at `.lbl` (run-detail.jsx:2237) but the expanded sub-rows read lowercase phrases ("Output" with capital, but the legacy/0118 piece labels mix capitalisations). The expanded total-in / total-out hierarchy from design-system §14 is missing entirely — there's only one combined output row today (run-detail.jsx:2274-2294). The "Total in" / "Total out" section-header pattern that 0100 specified never landed in code.

3. **No per-attachment surface.** The Consumption tab cannot show how many tokens an individual attachment consumes. The emitter at `src/dual_research/protocol/prompt_pieces.py` emits a single `user_prompt` aggregate; spec 0145 §1 decomposes that into `user_prompt.message` + `user_prompt.attachment.<id>`. Until that ships the card has nothing to surface; once it ships there's no rendering path. This spec ships the rendering path with a preview-row fallback so the visual lands before 0145's emitter side.

4. **Totals block does not exist.** Design-system §14 specifies a `.ccx-totals` block (`input billed · input cost · web search · cache savings · total input`). The CSS class is present (components.css:2597-2615) but no JSX site ever instantiates it — the run-detail.jsx render only has the single mono-line "Web search · N queries · $cost" at lines 2298-2306. Costs that the user wants to audit (input vs output vs search) are visible elsewhere in `CostsCluster` (run-detail.jsx:2326-2404), but the Consumption card itself doesn't have them. Adding `.ccx-totals` to the unfolded state closes the gap and consolidates the audit surface inside the card.

5. **Cost precision is wrong for a glance view.** The card uses the global `fmt.cost(...)` 4-decimal formatter for every cost display (run-detail.jsx:2245, 2292, 2304). On a 39-call run with per-call costs ranging from `$0.0260` (phase0-r1-openai) to `$0.2323` (phase0-r2-claude), 4-decimal precision creates visual noise and makes the card feel like an audit pane. The Consumption tab is a glance view; the audit surface is the run-detail footer (`$10.3127`) and the reconcile chip. Card-internal costs should be one-decimal (`$0.3`); the footer and reconcile keep 4-decimal.

The rework lands all five at once because they share the same five files (`run-detail.jsx`, `components.css`, `index.html`, `design-system/SPEC.md`, `design-system/assets/styles/composed-components.css`) and the same visual cluster. Doing them piecemeal across three minor versions would leave the card visibly inconsistent at every intermediate state.

This spec rewrites the **card-internal** anatomy and the per-attachment surface. It does **not** change cost data (0143), per-attachment emitter (0145), header polish on the run-detail page (0143), or the Compare-tab consumption view (handled by CSS inheritance — same `.ccx` rules flow through, no compare-specific tweaks).

---

## 2. Goals

1. **Single-percentage header, right-aligned to the bar end.** `.ccx-header` becomes a 3-column grid matching the bar-row grid (`140px 1fr 100px`, components.css:2541), so the `(X.X% of 1M)` percentage sits at column 2 with `justify-self: end` and lands at the same x-coordinate as the right edge of the bar fill below it. The chevron stays at column 3 with `justify-self: end`. Tokens and cost are removed from the header — they live at the right end of the bar (collapsed) or inside the totals block (unfolded).

2. **Capital-T section labels.** `Total tokens` (collapsed), `Total in` and `Total out` (unfolded section-header bars), and `Output` (unfolded output sub-row) all use capital T. The design system uses lowercase; this spec back-ports the capitalisation to design-system §14 in the same PR so the two sources don't drift.

3. **Per-attachment sub-rows in the unfolded view.** When `usage.promptPieces` carries `user_prompt.message` and `user_prompt.attachment.<id>` keys (post-0145), the unfolded view renders one sub-row per attachment in attachment-arrival order, labelled `Attachment · {title}` resolved through `DrArtifacts.displayName(id, { titleForId })` (artifacts.jsx). When only the legacy `userPrompt` aggregate is present (pre-0145), the renderer falls back to the spec-preview anatomy: two preview rows for `user_prompt.attachment.briefing` and `user_prompt.attachment.context` with a `preview` chip, dashed-outline styling, 0.62 opacity, and a diagonal-stripe overlay on the bar fill — flagging the row as extrapolated until the emitter lands.

4. **Totals block on the unfolded view.** Below the input sub-rows, render `.ccx-totals` with four lines (label left, value right, mirroring the bar-row pattern):
   - `input tokens · billed` — `fmt.tokens(tokensIn)` (verified: the anchor run's Claude phase0-r2 call has `input_tokens = 52,723`)
   - `input cost` — `fmtCost1(inputCost)` (anchor phase0-r2-claude: `cost_usd = 0.2323` → `$0.2`)
   - `web search · N queries` — `fmtCost1(searchCost)` (anchor phase0-r2-claude: `search_cost = 0.02` → `$0.0` displays, see §5.4 trade-off)
   - `total input` — `fmtCost1(inputCost + searchCost)` (rendered as `.line.is-grand` — bold rule above, larger value, components.css:2614-2615)

5. **One-decimal cost formatter scoped to the card.** A new `fmtCost1(n)` helper in run-detail.jsx applies to every cost display inside `CcxCard`. The global `fmt.cost(...)` keeps 4-decimal precision for the footer aggregate (`$10.3127`), the reconcile delta column, the per-turn status chips outside the Consumption tab, and tooltip strings.

6. **No regressions on the Compare tab, cross-run views, or the legacy/0118 piece vocabulary.** Pre-0118 runs (legacy 7-key vocabulary at `LEGACY_PIECE_KEYS` in run-detail.jsx:1974) still render via the existing legacy-vocab branch (run-detail.jsx:2170-2171). The new attachment-row path only activates when the canonical prefix `user_prompt.attachment.` appears in `promptPieces` or the preview-fallback condition fires.

---

## 3. Non-goals

- **No per-attachment emitter work.** Spec 0145 §1 owns the protocol/`pieces_for_*()` decomposition. This spec is the consumer.
- **No cost-data corrections.** Spec 0143 owns the cost/token capture parity work — making sure `usage.cost`, `usage.searchCost`, `usage.searches`, `usage.searchQueries` are accurate end-to-end. This spec reads whatever 0143 ships.
- **No run-detail header polish.** Spec 0143 §3 ships the top-bar copy button + Total cost/token label changes. Card-internal labels are this spec's scope; page-level header chrome stays out.
- **No protocol or contract changes.** No new `usage.*` fields. No new `promptPieces` schema. The `outputBreakdown` / `cacheSavingsUsd` fields proposed in B16 §10 (backend follow-up) are explicitly out of scope; the totals block omits the `cache savings · ×N reuse` line and the output sub-row list stays empty until those fields ship.
- **No canonical prompt-piece vocabulary refresh.** Spec 0145 §3 replaces the legacy UI piece vocabulary (`'system', 'brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'` at run-detail.jsx:1974) with canonical IDs. This spec piggybacks on 0145's helpers (`displayNameOf(id, attachmentTitles)`) but doesn't ship the vocabulary swap.
- **No `_canonicalToCamelKey` JS helper.** B16 §8 specified a JS helper mirroring `_to_camel` (server.py:1879). That work belongs to 0145 — every `promptPieces` consumer needs it, not just the Consumption card. This spec assumes the helper exists in `artifact-display.js` post-0145.
- **No closeout-row rendering.** `closeout.request` row stays suppressed until the aggregator emits `was_closeout: bool` per turn (B16 §10.4, backend follow-up). The preview-fallback path also omits it.
- **No Compare-tab visual changes.** Same `CcxCard` flows through to compare; CSS inheritance handles it. No compare-specific rules.
- **No mobile / sub-900 px breakpoint.** Run-detail is desktop-only; the existing `140px 1fr 100px` grid works down to ~720 px card width.

---

## 4. Current-state audit

### 4.1 — CcxCard JSX (run-detail.jsx)

| Element | File | Lines | Current state |
|---|---|---|---|
| `function CcxCard({ usage, agent, run, scale, expanded, onToggle, tourAnchor, phase })` | [run-detail.jsx:2117-2311](src/dual_research/ui/static/run-detail.jsx) | 2117–2311 | Renders header → total-tokens bar → reuse-signal mono line → (unfolded: divider → per-piece input rows → divider → output row → web-search mono line). No totals block. |
| Header markup | [run-detail.jsx:2215-2228](src/dual_research/ui/static/run-detail.jsx) | 2215–2228 | `<header className="ccx-header">[icon][nm][stats .pct][chev]`. `.stats` has `marginLeft: 'auto'` inline (line 2218); chevron is the rightmost child. The percentage sits next to the chevron, not above the bar end. |
| Total-tokens bar row | [run-detail.jsx:2232-2247](src/dual_research/ui/static/run-detail.jsx) | 2232–2247 | Inline grid `minmax(140px, 28%) 1fr minmax(110px, max-content)`. Label `Total tokens` (capital T). Right text `{fmt.tokens(totalTok)}t · {fmt.cost(cost)}` — 4-decimal cost. |
| Reuse signal mono line | [run-detail.jsx:2249-2258](src/dual_research/ui/static/run-detail.jsx) | 2249–2258 | `9.2kt seen · 246.1kt billed (× 27.0 token reuse) · 11.8kt out` — present on both collapsed and unfolded states when `reuse.hasReuse`. |
| Unfolded input rows | [run-detail.jsx:2261-2268](src/dual_research/ui/static/run-detail.jsx) | 2261–2268 | `grouped.rows.map(renderInputRow)`. `grouped` is from `groupPiecesForPhase(piecesRaw, phase)` (new-vocab branch) or `legacyGroupPieces(piecesRaw)`. No per-attachment row. No preview/synthetic flag. |
| Output row | [run-detail.jsx:2274-2294](src/dual_research/ui/static/run-detail.jsx) | 2274–2294 | Single `Output` row with `fl.out` / `fl.out-b` bar fill, `fmt.tokens(tokensOut)t · fmt.cost(outCostUsd)` right text. No reasoning / response / tool-calls breakdown. |
| Web-search mono line | [run-detail.jsx:2298-2306](src/dual_research/ui/static/run-detail.jsx) | 2298–2306 | `Web search · N queries · $cost` — present at the bottom of the unfolded section when `hasSearches`. Free-text, not in `.ccx-totals`. |
| `renderInputRow` | [run-detail.jsx:2178-2209](src/dual_research/ui/static/run-detail.jsx) | 2178–2209 | Inline 3-column grid per row. Right text `fmt.tokens(tokens)t · fmt.cost(propCost)` — 4-decimal cost. No `synthetic` flag handling. |
| ConsumptionView call site | [run-detail.jsx:1934-1943](src/dual_research/ui/static/run-detail.jsx) | 1934–1943 | Passes `usage, agent, run, scale, phase, expanded, onToggle, tourAnchor`. `phase` is `row.phase` (the phase number 0–4). `round` is **not** passed today; we'll need it for spec-preview round-conditional rows (§5.3). |

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

Five coordinated subsections. Each cites the exact file:line touched and the exact CSS token used.

### 5.1 — Header: 3-column grid, percentage right-aligned to bar end

Convert `.ccx-header` from flex to a grid that matches the bar-row grid below it. The closing `)` of `(X.X% of 1M)` lands at the same x-coordinate as the right edge of the bar fill — verifiable programmatically with `stats.getBoundingClientRect().right === bar.getBoundingClientRect().right`.

**CSS patch** ([components.css:2509-2527](src/dual_research/ui/static/components.css), replacing the existing rules):

```css
.ccx-header {
  display: grid;
  grid-template-columns: 140px 1fr 100px;
  align-items: center;
  gap: 12px;
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

The `margin-left: auto` on `.stats` is **removed** (flex semantics don't apply under grid). `.stats { white-space: nowrap; }` prevents the percentage from wrapping when cards render side-by-side at 1280 px viewport.

**JSX patch** ([run-detail.jsx:2215-2228](src/dual_research/ui/static/run-detail.jsx)):

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

The `.pct` and `.sep` child spans inside `.stats` ([components.css:2526-2527](src/dual_research/ui/static/components.css)) become unused because `.stats` itself now holds only the bracketed percentage. The two `.pct` / `.sep` rules can be left in place (no harm) or removed in a cosmetic pass.

### 5.2 — Spec-0145 per-attachment surface (`buildSpec0145InputBuckets`)

The unfolded view renders one sub-row per `user_prompt.attachment.<id>` key in `usage.promptPieces` when 0145's emitter is live. Before 0145 lands, the same surface renders a 2-row preview placeholder so the visual is in production before the data.

**0145 data contract** (from B15 — see `specs/_backlog-inventory.md` lines 248-261; canonical-key list verbatim from spec 0145's §1):

```
P0  → system.task.input,         user_prompt.message, user_prompt.attachment.<id>×N, prior_turns.phase0, ledger.standing_items, closeout.request
P1  → system.task.research_plan, user_prompt.message, user_prompt.attachment.<id>×N, phase0.agreement.interpretation
P2  → system.task.plan_negotiation, user_prompt.message, user_prompt.attachment.<id>×N, phase0.agreement.interpretation, phase1.claude, phase1.openai, prior_turns.phase2, ledger.standing_items, closeout.request
P3  → system.task.drafting,      user_prompt.message, user_prompt.attachment.<id>×N, phase0.agreement.interpretation, phase1.claude, phase1.openai, phase2.agreement.plan, all_p2_turns, carry_forward.phase2
P4  → system.task.review,        user_prompt.message, user_prompt.attachment.<id>×N, current_draft, prior_turns.phase4, ledger.standing_items, closeout.request
```

The aggregate `user_prompt` key is **dropped** by 0145. Per-key tokens arrive as `dict[str, int]` keyed by canonical ID; on the JS side those become camelCased keys via `_canonicalToCamelKey` (shipped by 0145 in `artifact-display.js`). The Consumption card calls `displayNameOf(canonicalId, attachmentTitles)` from `artifact-display.js` to resolve every label.

**JS helper added to `run-detail.jsx`** (~140 LOC; placed near the existing `groupPiecesForPhase` at run-detail.jsx:1980+):

```javascript
// Spec-0145 canonical input piece order per phase. Mirrors the emitter's
// pieces_for_*() output. `<id>` placeholders in attachment slots expand
// to one row per attachment in arrival order.
const SPEC_0145_PHASE_PIECES = {
  0: ['system.task.input',           'user_prompt.message', 'user_prompt.attachment.<id>', 'prior_turns.phase0', 'ledger.standing_items'],
  1: ['system.task.research_plan',   'user_prompt.message', 'user_prompt.attachment.<id>', 'phase0.agreement.interpretation'],
  2: ['system.task.plan_negotiation','user_prompt.message', 'user_prompt.attachment.<id>', 'phase0.agreement.interpretation', 'phase1.claude', 'phase1.openai', 'prior_turns.phase2', 'ledger.standing_items'],
  3: ['system.task.drafting',        'user_prompt.message', 'user_prompt.attachment.<id>', 'phase0.agreement.interpretation', 'phase1.claude', 'phase1.openai', 'phase2.agreement.plan', 'all_p2_turns', 'carry_forward.phase2'],
  4: ['system.task.review',          'user_prompt.message', 'user_prompt.attachment.<id>', 'current_draft', 'prior_turns.phase4', 'ledger.standing_items'],
};

// Two-row preview placeholder used when run.attachments is missing
// (every shipped run today). Replaced automatically when the backend
// surfaces real attachments in run.attachments.
const PREVIEW_ATTACHMENTS = [
  { id: 'briefing', title: 'Briefing document' },
  { id: 'context',  title: 'Supplementary context' },
];

// Fill-class mapping for each canonical-piece prefix. Mirrors the
// design-system §14 colour lanes; reads from .ccx-bar .fl.<class> rules.
const FILL_CLASS_FOR = {
  'system':       'sys',
  'user_prompt':  'round',
  'prior_turns':  'hist',
  'phase':        'hist',          // phase1.claude, phase2.agreement.*, etc.
  'all_p2_turns': 'hist',
  'current_draft':'round',
  'carry_forward':'round',
  'ledger':       'round',
  'closeout':     'round',
};

function fillClassFor(canonicalId) {
  const prefix = canonicalId.split('.')[0];
  return FILL_CLASS_FOR[prefix] || 'round';
}

// Build the input-row list for an unfolded card. Returns rows in
// canonical-arrival order, with `synthetic: true` on rows that are
// extrapolated (key not present in piecesRaw — only the legacy
// userPrompt aggregate is, etc.).
function buildSpec0145InputBuckets(piecesCamel, attachments, phase, round, run) {
  const template = SPEC_0145_PHASE_PIECES[phase] || [];
  const atts = (attachments && attachments.length) ? attachments : PREVIEW_ATTACHMENTS;
  const rows = [];
  for (const id of template) {
    // Round-conditional: prior_turns.* is omitted on round 1.
    if (id.startsWith('prior_turns.') && (round || 1) === 1) continue;
    // Attachment template: expand to one row per attachment.
    if (id === 'user_prompt.attachment.<id>') {
      for (const a of atts) {
        const realId = `user_prompt.attachment.${a.id}`;
        const camelKey = _canonicalToCamelKey(realId);
        const realTokens = Number(piecesCamel?.[camelKey]) || 0;
        const synthetic = realTokens === 0 && !run?.attachments;
        rows.push({
          id: realId,
          label: window.DrArtifacts.displayName(realId, { titleForId: () => a.title }),
          tokens: realTokens,
          fillClass: 'round',
          synthetic,
        });
      }
      continue;
    }
    const camelKey = _canonicalToCamelKey(id);
    let realTokens = Number(piecesCamel?.[camelKey]) || 0;
    // Backward-compat fallback: pre-0145 runs emit a single aggregate
    // `userPrompt` key. Route it to the canonical .message row.
    if (realTokens === 0 && id === 'user_prompt.message') {
      realTokens = Number(piecesCamel?.userPrompt) || 0;
    }
    const synthetic = realTokens === 0;
    rows.push({
      id,
      label: window.DrArtifacts.displayName(id, {}),
      tokens: realTokens,
      fillClass: fillClassFor(id),
      synthetic,
    });
  }
  return { rows };
}
```

When the backend ships 0145 §1, `piecesCamel` contains real `userPrompt.attachment.{id}` keys; `synthetic` flips to false automatically and the preview styling falls off. No card-side code change at that point.

### 5.3 — Spec-preview row anatomy (visual marker for `synthetic: true`)

Three subtle markers on `.ccx-sub-row.is-preview`:

1. `opacity: 0.62` on the whole row.
2. Diagonal-stripe overlay on the bar fill: `repeating-linear-gradient(45deg, transparent 0 4px, rgba(255,255,255,0.18) 4px 6px)` (light-mode swaps to `rgba(0,0,0,0.18)` per `body.light` selector mirroring the existing `.ccx-bar .reuse` light-mode rule at [components.css:2579-2582](src/dual_research/ui/static/components.css)).
3. A `preview` chip rendered in the `.num` slot, before the token count: dashed `1px solid var(--md-on-surface-faint)` outline, transparent fill, font `var(--md-w-medium) var(--md-label-s-size) var(--md-font-plain)`, padding `1px 6px`, border-radius `var(--md-shape-xs)`.

**CSS additions** (append to the existing `.ccx-bar-row, .ccx-sub-row` block at [components.css:2540](src/dual_research/ui/static/components.css)):

```css
.ccx-sub-row.is-preview { opacity: 0.62; }
.ccx-bar .fl.is-preview-overlay {
  background-image: repeating-linear-gradient(45deg,
    transparent 0 4px,
    rgba(255,255,255,0.18) 4px 6px);
  background-blend-mode: overlay;
}
body.light .ccx-bar .fl.is-preview-overlay {
  background-image: repeating-linear-gradient(45deg,
    transparent 0 4px,
    rgba(0,0,0,0.18) 4px 6px);
  background-blend-mode: normal;
}
.ccx-preview-chip {
  display: inline-flex; align-items: center;
  padding: 1px 6px;
  border: 1px dashed var(--md-on-surface-faint);
  border-radius: var(--md-shape-xs);
  color: var(--md-on-surface-faint);
  font: var(--md-w-medium) var(--md-label-s-size)/1 var(--md-font-plain);
  letter-spacing: 0.04em;
  text-transform: lowercase;
  margin-right: 6px;
}
```

**Tooltip** on each preview row: `Preview · the backend doesn't yet emit ${id}; this row is extrapolated (spec 0145).`

**Renderer change** in `renderInputRow` ([run-detail.jsx:2178-2209](src/dual_research/ui/static/run-detail.jsx)): when `row.synthetic === true`, the `<div>` gets `className="ccx-bar-row ccx-sub-row is-preview"`, the bar fill gets a layered `is-preview-overlay` class, and the `.num` slot prepends `<span className="ccx-preview-chip" title="…">preview</span>` before the token + cost text. When `row.tokens === 0` and `synthetic === true`, the bar fill width is the row's piece percent (which is 0% — the bar is empty and the stripe overlay does the visual work).

### 5.4 — Totals block on the unfolded view

Replace the free-text web-search mono line at [run-detail.jsx:2298-2306](src/dual_research/ui/static/run-detail.jsx) with a `.ccx-totals` block, rendered after the output row.

**JSX patch** (replaces the existing `hasSearches` mono div):

```jsx
<div className="ccx-totals">
  <div className="line">
    <span className="l">input tokens · billed</span>
    <span className="v">{fmt.tokens(tokensIn).toLocaleString()}</span>
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
- `input cost` → `$0.2` (after subtracting output cost; `inputCost = tokenCost - outCostUsd` per existing `CcxCard` logic at run-detail.jsx:2148)
- `web search · 2 queries` → `$0.0` (`fmtCost1(0.02)` = `$0.0`; see §5.5 trade-off)
- `total input` → `$0.2`

The `cache savings · ×N reuse on Xk` line from design-system §14 is **omitted** until backend ships `usage.cacheSavingsUsd` (B16 §10.2, out-of-scope for this spec).

### 5.5 — `fmtCost1` helper + scoped application

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
- Total-tokens bar right text ([run-detail.jsx:2245](src/dual_research/ui/static/run-detail.jsx))
- Per-input-row right text (inside `renderInputRow` at [run-detail.jsx:2205](src/dual_research/ui/static/run-detail.jsx))
- Output-row right text ([run-detail.jsx:2292](src/dual_research/ui/static/run-detail.jsx))
- Every totals-block `.v` (§5.4)

The global `fmt.cost(...)` keeps 4-decimal precision and is unchanged for:
- Run-detail footer aggregate (`$0.5076 + $1.8051 = $10.3127` — verified against the anchor run's `total_cost_usd`)
- Reconcile delta column
- Per-turn status chips outside the Consumption tab
- Tooltip strings

**Sub-cent cost trade-off.** `fmtCost1(0.02)` → `$0.0`, which reads as "free" on cards that ran one search. The anchor run has `total_search_cost_usd = 0.865` and 14 of 39 calls had `search_cost > 0` — at one-decimal precision most per-call search costs render as `$0.0` or `$0.1`. The default for this spec is to keep `$0.0`; if user-testing flags the "free" misread, a `<$0.1` representation for non-zero sub-5¢ amounts is a one-line follow-up. See §10 open question.

### 5.6 — `index.html` cache-buster bump

Bump the `?v=` query parameter on every CSS + JSX import in [index.html](src/dual_research/ui/static/index.html) from `?v=0138a` → `?v=0146a`. Mechanical, ~40 lines.

### 5.7 — `round` plumbed through to `CcxCard`

`ConsumptionView` at [run-detail.jsx:1934-1943](src/dual_research/ui/static/run-detail.jsx) does not currently pass `round`. The `round` is on each row in the consumption-row list as `row.round`. Add `round={row.round}` to the `<CcxCard …>` invocation (1 line). Inside `CcxCard`, destructure `round` from props and pass it to `buildSpec0145InputBuckets(piecesCamel, run?.attachments, phase, round || 1, run)`. The `round-conditional handling for `prior_turns.*` rows depends on this — without `round`, R1 cards show a preview row for `prior_turns.phase{N}` that shouldn't exist.

### 5.8 — Design-system back-port

Four updates to `design-system/SPEC.md` §4.3 + the example HTML (`design-system/assets/Design System v2.html` §14) + `design-system/assets/styles/composed-components.css`, all in this PR:

1. **Header trio collapses to single percentage**, right-aligned to bar end. Document the `(X.X% of 1M)` placement at column 2 with `justify-self: end`.
2. **Capital-T labels** (`Total tokens`, `Total in`, `Total out`, `Output`) replace the lowercase reference.
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

### 7.1 — Unit (JS, Vitest / inline `node --test` parity)

- [ ] `fmtCost1(0.5028) === '$0.5'`
- [ ] `fmtCost1(0.02)   === '$0.0'`
- [ ] `fmtCost1(undefined) === '$0.0'`
- [ ] `fmtCost1(10.3127) === '$10.3'` (anchor `total_cost_usd`)
- [ ] `buildSpec0145InputBuckets({}, [], 2, 1, {})` returns the P2 piece order **minus** `prior_turns.phase2` (R1 suppression).
- [ ] `buildSpec0145InputBuckets({}, [], 2, 3, {})` returns the P2 piece order **including** `prior_turns.phase2`, marked `synthetic: true`.
- [ ] `buildSpec0145InputBuckets({ userPrompt: 5251 }, [], 2, 3, {})` returns a row where `id === 'user_prompt.message'`, `tokens === 5251`, `synthetic === false` (backward-compat fallback path).
- [ ] `buildSpec0145InputBuckets({ 'userPrompt.message': 400 }, [], 2, 3, {})` returns the canonical key value, **not** the legacy aggregate, when both are present.
- [ ] `buildSpec0145InputBuckets({}, [], 2, 1, {})` returns two `user_prompt.attachment.*` rows resolving to `Briefing document` / `Supplementary context` (PREVIEW_ATTACHMENTS fallback).
- [ ] `buildSpec0145InputBuckets({}, [{ id: 'briefing', title: 'Custom briefing' }], 2, 1, {})` returns ONE attachment row labelled `Attachment · Custom briefing` (real attachments preferred over preview).

### 7.2 — Pixel alignment

- [ ] After the header grid lands, programmatic check: for every `.ccx` on the Consumption tab of the anchor run, `stats.getBoundingClientRect().right === bar.getBoundingClientRect().right` (within 1px).
- [ ] The `(X.X% of 1M)` percentage does not wrap when the run-detail viewport is 1280 px wide (cards rendered side-by-side via `.cards-2up`).

### 7.3 — Visual / integration (manual)

- [ ] Open `/#/runs/20260521-010637-dvs-backend-language-choice` → Consumption tab.
  - [ ] Header reads `[icon][Claude]                         (X.X% of 1M) [chevron]` with the closing `)` directly above the right edge of the bar fill.
  - [ ] Collapsed view shows a single `Total tokens` bar with `Xkt · $X.X` at the right (one-decimal cost).
  - [ ] Cache-reuse stripe is visible on the OpenAI bars (cache_read = 88,448 tokens on this run).
- [ ] Expand the P0-R2-Claude card. Verify:
  - [ ] `Total in` (capital T) and `Output` (capital O) are present as section/sub bars.
  - [ ] Input sub-rows render in 0145 arrival order (today, all synthetic since 0145 hasn't shipped): `Drafting instructions` → `Chat message` (from `userPrompt` fallback, not synthetic) → 2× `Attachment · …` (preview chip, dashed outline, stripe overlay) → no `Prior negotiation turns` row (P0 R2 still renders it if R≥2; verify).
  - [ ] Totals block: `input tokens · billed   52,723` / `input cost $0.2` / `web search · 2 queries $0.0` / `total input $0.2` (bold rule above).
- [ ] Expand the P2-R1 card. Verify `Prior negotiation turns` is **omitted** (R1).
- [ ] Expand the P2-R2 card. Verify `Prior negotiation turns` **appears** marked `preview` (since 0145 hasn't shipped, it's synthetic).
- [ ] Light-mode parity: toggle `.light` body class. The preview-stripe overlay swaps to the dark-pattern variant; the totals block reads on cream.
- [ ] Compare tab: open two runs side-by-side. Confirm both Consumption panes render with the same header anatomy and totals block, no compare-specific regressions.

### 7.4 — Visual regression snapshots

- [ ] Capture the Consumption tab at:
  - `/#/runs/20260521-010637-dvs-backend-language-choice` (P0–P4 deadlocked; 39 calls; total `$10.3127`)
  - One additional run with multiple real attachments once 0145 lands, to verify the synthetic markers fall off.
- [ ] Capture light + dark variants.
- [ ] Before/after diff: the only intended deltas are §5.1–§5.5 changes. Anything else flagged is a regression.

### 7.5 — Cache bust

- [ ] After deploy, hard-reload the run-detail page; confirm the new anatomy renders (i.e. the `?v=0146a` cache-bust took effect).

### 7.6 — Backward compatibility

- [ ] Open a pre-0118 run (legacy 7-key vocab; e.g. `LEGACY_PIECE_KEYS = ['brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp']`). The legacy renderer path at [run-detail.jsx:2170-2171](src/dual_research/ui/static/run-detail.jsx) is unchanged — verify the card renders with the legacy labels and no preview chips appear.
- [ ] Open a 0118-vocab run pre-0145 (canonical `system.task.*`, aggregate `user_prompt`). The new renderer path activates; the aggregate routes to `Chat message` via the §5.2 fallback and the 2× preview attachments render.

---

## 8. Risks

- **Header overflow at narrow widths.** Cards rendered side-by-side at < 900 px viewport could push the percentage into the chevron column. **Mitigation:** `white-space: nowrap` on `.stats` + verified down to 720 px during the prototype walkthrough. If a narrower viewport ever surfaces wrapping, drop the col-2 `1fr` to `minmax(80px, 1fr)` so the chevron column overflows first.
- **`fmtCost1` reading as "free" on sub-cent costs.** `$0.02` → `$0.0` on cards that ran a single search. On the anchor run, this affects ~14 of 39 calls. **Mitigation:** open question §10.1 decides whether to switch to `<$0.1` for non-zero sub-5¢ amounts. Default keeps `$0.0`; the totals block + run-detail footer carry the audit truth.
- **Preview placeholders mistaken for real data.** Three visual markers (opacity, stripe, chip) plus the tooltip text. **Mitigation:** the chip text is `preview` (not `est` or `~`); the tooltip explicitly says "extrapolated (spec 0145)". When 0145 ships the synthetic flag flips off automatically — no user-facing transition state to manage.
- **CSS-token drift between `components.css` and `composed-components.css`.** Two surfaces, two file paths; the design-system audit workflow doesn't yet diff them in CI. **Mitigation:** §5.8 includes the design-system mirror update in the same PR; the manual diff happens once at review time. A CI-level diff is a follow-up for the design-system audits workflow (not this spec).
- **Visual regression on adjacent consumption views.** Compare tab + Search-palette previews + cross-run hover cards all use the same `.ccx` rules. **Mitigation:** §7.3 manual pass covers the Compare tab; Search-palette and cross-run hover don't render full `CcxCard` (different component path), so they're insulated. Confirm during review.
- **Cache-bust forgotten.** Repeat of every prior visual spec's risk. **Mitigation:** §7.5 makes it explicit; the bump from `?v=0138a` to `?v=0146a` is mechanical (find-replace across 40 lines in `index.html`).
- **Spec 0145 ships after 0146.** This spec is the consumer; if 0145's emitter ships in a later release the preview rows stay marked `synthetic` until then. Acceptable — that's the whole point of the spec-preview rendering. The only risk is users misreading the preview rows as "the feature is broken"; the chip text + tooltip mitigate.
- **Spec 0145 ships before 0146 in the same window.** If 0145 lands first the canonical keys are already in `promptPieces`; rows render with `synthetic: false` and the preview chip falls off — exactly the intended end state. No code change needed.

---

## 9. Files touched (concrete list)

```
src/dual_research/ui/static/run-detail.jsx
  - rewrite CcxCard header markup (≈14 LOC)
  - add fmtCost1 helper (≈4 LOC)
  - add buildSpec0145InputBuckets + SPEC_0145_PHASE_PIECES + PREVIEW_ATTACHMENTS + FILL_CLASS_FOR + fillClassFor (≈140 LOC)
  - rewrite renderInputRow to handle `synthetic` flag + preview chip (≈30 LOC)
  - add .ccx-totals JSX block in the unfolded section (≈22 LOC)
  - swap to fmtCost1 at the 3 cost callsites inside CcxCard (≈3 LOC)
  - ConsumptionView passes round={row.round} to CcxCard (1 LOC)
  - destructure `round` in CcxCard props (1 LOC)

src/dual_research/ui/static/components.css
  - .ccx-header → grid (≈10 LOC, replaces existing flex)
  - .ccx-header .hd-id new rule (≈4 LOC)
  - .ccx-header .stats { justify-self: end; white-space: nowrap; … } (≈8 LOC, replaces existing flex margin-left:auto)
  - .ccx-header .chev { justify-self: end; … } (1 LOC additive)
  - .ccx-sub-row.is-preview + .ccx-bar .fl.is-preview-overlay + light variant + .ccx-preview-chip (≈22 LOC)

src/dual_research/ui/static/index.html
  - bump ?v=0138a → ?v=0146a across all CSS + JSX imports (≈40 LOC, mechanical)

design-system/assets/styles/composed-components.css
  - mirror the .ccx-header grid changes from components.css (matches §5.1)

design-system/SPEC.md
  - rewrite §4.3 "Consumption card" per §5.8

design-system/assets/Design System v2.html
  - rewrite §14 anatomy + examples per §5.8
  - update the consumption HTML mocks for the new collapsed + unfolded look

design-system/CHANGELOG.md
  - new entry for spec 0146
```

No backend, no protocol, no contract changes. No Python edits except whatever 0143 / 0145 are already shipping in this batch.

---

## 10. Open questions

1. **Sub-cent cost display (§5.5).** Keep `$0.0` for non-zero amounts under 5¢, or switch to `<$0.1` for that range? Default: keep `$0.0` — the totals block + run-detail footer carry the audit truth, and one-decimal precision in the card is a deliberate glance-view choice. Revisit if user-testing flags the "free" misread.

2. **`fmtCost1` scope creep — apply to footer aggregate too?** The run-detail footer renders `$10.3127` (4-decimal). For consistency we could swap that to `fmtCost1` → `$10.3`. Default: keep 4-decimal in the footer; it's the audit number, the card is the glance. Confirm before merging.

3. **Capital-T labels (§5.1, §5.2, §5.4) — keep or revert to lowercase?** This spec back-ports capitalisation to design-system §14. The alternative is lowercase everywhere for design-system parity. Default: capital T, since the user signed off on it during the prototype walkthrough; design-system updates in §5.8 lock it in.

4. **`closeout.request` row — render as preview anyway?** B16 §10.4 keeps it suppressed until the aggregator emits `was_closeout: bool`. Should we render it as a preview row on every P0 / P2 / P4 round so users know it exists, with a tooltip saying "only fires on closeout"? Default: suppress until the backend lands; preview-row noise vs. honesty about what data we have. Revisit if the user wants more visibility into round structure.

5. **Preview-row totals reconciliation.** The synthetic rows' tokens are NOT summed into `input tokens · billed` (the total comes from real `usage.in`). When real + synthetic overlap, row totals can exceed the billed total. Worth surfacing as a tooltip ("real subtotal · NN%") or just leaving it? Default: leave it; it's a known artifact of preview mode and the `synthetic` chip already communicates the source.
