---
spec: 0035
title: Consumption rework + header-placement fix + app-version chip
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.33.0
created: 2026-05-16
pr: ""
---

# Spec 0035 — Consumption rework + header-placement fix + app-version chip

## Context

The third and final spec from the post-spec-0032 test-run feedback. Four
gaps in the Consumption tab, plus one small piece of chrome.

1. **The 1M-token scale buries small consumption.** Every bar on the
   Consumption tab is sized to the model's full context window — 1M for
   the prod tier. Real per-turn input runs ~10–80K tokens. At that
   ratio the bar fills barely 1–8% of the available width and the
   user can't see *anything* — neither the relative size of pieces
   nor the round-over-round growth. Spec 0029 picked context-window-
   relative widths so different runs would be comparable; spec 0030
   added per-piece segments inside the same bar. Both decisions are
   right at large scale and wrong at the small scale that actually
   happens.

2. **One bar, two lanes, segmented inside.** Today each Consumption
   row renders as a 3-column grid: phase label · Claude lane · OpenAI
   lane. Each lane is one horizontally-segmented bar (brief | d1 | d2
   | plan | hist | …). To read which piece consumed what, the user
   has to hover for tooltips or squint at adjacent segment widths
   that are 1–3 pixels wide. The user wants this restructured: when
   a row is expanded, render a per-agent card below it with the
   **total bar at the top** and **one stacked bar per input piece**
   beneath, each at the same scale, each with a distinct color and an
   explicit label.

3. **Sub-input colors collide with agent colors.** The current
   per-piece palette in `KIND_COLORS` overlaps the agent totals:
   `d1` is Claude-orange, `d2` is GPT-green, `plan` is the same green
   as `ok` status. When the total bar (in the agent's own color)
   sits next to the per-piece bars (some of which are also that
   color), the user can't tell at a glance which is the aggregate
   and which is a piece. The user explicitly asked: keep agent
   colors for the totals; pick distinct colors for the sub-inputs.

4. **No reference marker for the full context window.** Once the bar
   is sized to the data (item 1), the user loses the awareness of
   how much *headroom* they have. A vertical tick marker at the
   1M-token position (or wherever the model's actual cap sits) on
   the data-scaled bar keeps both signals: "how much of the budget
   did this round actually consume" + "how much budget existed."

5. **App version is invisible from the UI.** Right now there's no
   way to tell, without opening a terminal, what version of
   dual-research is live in front of you. With three specs landing
   in two days, this is a real audit gap — the user just deployed
   v0.32.0 but the only confirmation is `curl /api/health`. A small
   `v0.32.0` chip in the chrome (top or bottom bar) reading the
   version from `/api/health` would fix this in one render.

6. **Spec 0033's header rework over-claimed real estate.** The
   four-row run header was too tall and put per-agent strips +
   Conversation/Consumption tabs into chrome that should have been
   simpler. Two corrections, both folded into this spec so we
   don't pay a separate run + verify cycle:

   - The Claude / GPT activity strips belong **inside the Timeline
     pane**, not in the run header. They duplicate the existing
     `AgentLegendChip`s in the Timeline toolbar today; spec 0033
     should have merged the two, not added a second copy. Move the
     strips down and replace the chips — single source of truth for
     per-agent state.
   - The Conversation / Consumption tabs belong **inside the
     Timeline pane** too, below the pane title. Spec 0033's
     prominent visual treatment (font bump + accent underline) is
     correct and carries forward; only the *position* moves back.

   The run header collapses from four rows to two: topic + cost +
   status on row 1, phase dots + meta on row 2.

Prior context: spec 0029 (Consumption tab v1), spec 0030 (per-piece
segments + real context windows), spec 0031 (tier-lookup fallback +
click-to-expand + per-phase web-search count + cost). This spec
finishes the Consumption-tab visualisation story by reshaping how
small numbers render and re-using the existing per-piece data
(`prompt_pieces` on `TurnTokenUsage`) without changing the data
model at all.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **Bar scale is data-relative by default, with a vertical tick at the context-window position.** | The bar fills against `max(observed_consumption_across_rows) × 1.15` (15% headroom for the largest row). A muted vertical line at the model's `context_window` position labelled `1M` (or `200K` / `400K`) keeps the budget signal visible. When the actual consumption EXCEEDS the heuristic (rare), the bar extends past the marker and the scale auto-grows. |
| D2 | **Scale is computed per-grid, not per-row.** | All bars in the same Consumption tab view share the same denominator so they're directly comparable. Recomputed when the row data changes (live updates). A small "scale: 87K tokens · cap 1M" caption sits at the top of the grid so the user knows what they're looking at. |
| D3 | **Expanded-row layout: two side-by-side per-agent cards, each carrying a stacked-bar block.** | Today's expanded row is a single 3-column row of totals (kind label · Claude tokens · OpenAI tokens). New layout: a 2-column grid (Claude card · GPT card) under the row. Each card has its agent name + total bar at top, then one stacked sub-bar per input piece in canonical order (`brief`, `d1`, `d2`, `plan`, `hist`, `draft`, `histp`), each with a label, token count, and bar at the same scale as the total. Cards collapse on the same click that expanded them. |
| D4 | **Sub-input bar colors are a neutral palette explicitly distinct from agent colors.** | New `SUBINPUT_COLORS` map replaces the per-kind colors used for sub-bars (not the segment fills on the *collapsed* row — those keep their existing palette for the segmented compact view). Palette: indigo, slate, teal, rose, ochre, sage, plum — none of which can be confused with Claude-amber or GPT-green. The total bar keeps `var(--agent-a)` / `var(--agent-b)` so the agent identity reads at a glance. |
| D5 | **Collapsed row keeps today's compact segmented bar.** | Spec 0030's `brief / d1 / d2 / plan / hist / draft / histp` segmented bar inside ONE bar (per agent lane) survives unchanged in the collapsed row. Reasons: (a) collapsed view is for skimming round-by-round growth — segments inside one bar communicate that better than 7 stacked sub-bars × 2 lanes per row; (b) the rework is about the *expanded* view, where the user wants to read exact values. |
| D6 | **Bar scale auto-zooms separately for collapsed and expanded views.** | Same denominator (per-grid max × 1.15) for both, but the expanded view's per-piece sub-bars are scaled to the SAME denominator as the totals so they read proportionally — a tiny `brief` bar next to a huge `hist` bar is the intent. No per-bar local normalisation. |
| D7 | **Sub-bars in expanded cards are sorted by descending size by default, with a toggle for "canonical (Tk) order".** | When investigating "why is this turn so big," sort-by-size answers the question immediately. The user can flip to the canonical Tk order (`brief, d1, d2, plan, hist, draft, histp`) to walk pieces in protocol order. Stored per-card; resets on run-id change. |
| D8 | **Empty pieces (token count = 0) collapse to a single-line "(N not used in this turn)" footnote at the bottom of the card.** | The Tk-vocab has 7 keys but a Phase 1 turn only uses 1 of them; rendering 6 zero-width bars is noise. Footnote shows which were skipped so the user can confirm "yes, Phase 1 only inlines the brief." |
| D9 | **App-version chip in the chrome bar's right corner.** | Renders `v{version}` (font-mono, muted) sourced from `/api/health` fetched once on app mount. Position: leftward of the existing "All runs / Help / Settings" tabs in the top chrome (not the run-detail header — the version is global chrome, not run-specific). On click, opens the how-it-works page (existing route) anchored at the VERSION_NOTES section. Tooltip: `dual-research v{version} · click for release notes`. |
| D10 | **`/api/health` is already public in both fs + supabase modes.** | No backend changes for the version chip. Existing endpoint returns `{ok, version, ...}`. The fetch is one round-trip on app mount, cached in a top-level React state, broadcast to consumers via the existing `RunContext` or a new `AppMetaContext`. v1 just hangs it on `window.__appMeta` (simple, matches the project's window-export pattern). |
| D11 | **No data-model changes.** | The Consumption rework is pure visualisation — every input is already in `TurnTokenUsage.prompt_pieces` (spec 0030). The version chip needs only the existing `/api/health` payload. This spec is the smallest of the three by code surface. |
| D12 | **Web-search count + cost rows in the expanded view stay.** | Spec 0031 added per-phase web-search count + tool cost in the expanded body. They're orthogonal to the per-piece visualisation (search results don't appear as a Tk piece) and the user didn't ask to remove them. They render below the per-piece block in the same per-agent card, with the same colour treatment as today. |
| D13 | **Run header reverts from four rows to two.** | Row 1: topic + cost + status/errors (no tabs, no agent strips). Row 2: phase dots + dot labels + run metadata (started · drafter · elapsed · round). The four-row variant from spec 0033 — including per-agent strips and the tab pill — is dismantled. `RunDetailHeader`'s `tab` / `onTabChange` props are removed; the Timeline pane owns the tab state again. |
| D14 | **Per-agent activity strips move into the Timeline pane and replace `AgentLegendChip`.** | The strip's payload (`[icon] [name] [model] [tokens·cost] │ [● status sentence]`) is exactly what `AgentLegendChip` aspired to, plus the live-activity sentence. Single component, single location. The pill aesthetic (rounded, `var(--bg-2)` background, agent-border) survives; the existing 2px left-border-rail from spec 0033's header variant is dropped (the pill border IS the rail). |
| D15 | **The two agent pills land on the two existing Timeline-pane header rows — one per row.** | The Timeline pane already has two horizontal rows of chrome above the cards: row 1 is the `PaneHeader` (`Timeline · N artifacts`); row 2 is the `PaneToolbar` (today holds the two `AgentLegendChip`s). Spec 0035 puts **Claude on the right of row 1** (same row as the pane title) and **GPT on the right of row 2** (where the badges used to sit). Vertically the two pills line up — same right-edge column on consecutive rows. The Conversation / Consumption tabs join row 2 to GPT's right. The live-count chip also sits on row 2 between GPT and the tabs. No `flex-wrap` magic — this layout is deliberate at every viewport. |
| D16 | **`composeAgentActivity` is unchanged.** | The phrase / live-flag computation lives in `run-detail.jsx` and the new pill consumes it identically. Pure relocation of the chrome. |
| D17 | **Timeline pane state ownership reverts to spec-0030's pattern.** | `Timeline` once again owns its own `tab` state internally; `RunDetail` no longer threads `timelineTab` / `setTimelineTab` props. The lifting introduced in spec 0033 (so the header could render the tabs) is unwound. |

## Proposed change

### 1. Dynamic scale + context-window marker — `run-detail.jsx`

`ConsumptionView` (line ~598) computes a new `scale` value from the
rows:

```js
function computeConsumptionScale(rows, run) {
  // Walk every (row, agent, usage) and find the max non-output
  // consumption (input + cache_read sum).
  let maxConsumption = 0;
  let maxWindow = 0;
  for (const row of rows) {
    for (const ag of ['claude', 'gpt']) {
      const u = row[ag];
      if (!u) continue;
      const consumed = (u.in || 0) + (u.cacheRead || 0);
      if (consumed > maxConsumption) maxConsumption = consumed;
      const w = contextWindowFor(u, run, ag);
      if (w > maxWindow) maxWindow = w;
    }
  }
  if (maxConsumption === 0) return { denom: 128_000, window: 128_000, dataRelative: false };
  const headroom = Math.round(maxConsumption * 1.15);
  // If actual consumption is already > window (impossible but defensive),
  // grow the scale; otherwise pick max(headroom, observed window).
  // But default to data-relative — the window marker still shows.
  return { denom: headroom, window: maxWindow, dataRelative: true };
}
```

Threaded into `TokenBar` (line ~868) and the new stacked-bar renderer
via a `scale` prop. Each bar's width % = `value / scale.denom`. A new
`ContextWindowMarker` renders a 1px vertical line + a small label
(`1M`, `200K`, …) at the `scale.window / scale.denom` position when
`window > denom` (otherwise the window IS the scale).

A caption above the grid: `scale: 87K tokens · cap 1M` so the user
knows the bars are data-relative, not budget-relative.

### 2. Expanded per-agent cards — `run-detail.jsx`

`ConsumptionRowExpanded` (line ~719) is rewritten. New layout:

```
┌─ Claude card ───────────────────┐  ┌─ GPT card ─────────────────────┐
│ ◉ Claude · 42,180 t (4.2% of 1M)│  │ ◉ GPT · 38,720 t (3.9% of 1M)   │
│ ████████░░░░░░░░░░ total        │  │ ███████░░░░░░░░░░░ total        │
│   ───────────────────────────── │  │   ───────────────────────────── │
│   brief    ███░░░░ 8,120 t      │  │   brief    ███░░░░ 8,120 t      │
│   d1       ████░░░ 11,200 t     │  │   d1       ████░░░ 11,200 t     │
│   hist     ████████ 18,460 t    │  │   hist     ███████░ 17,200 t    │
│   d2       █░░░░░░ 4,400 t      │  │   d2       █░░░░░░ 2,200 t      │
│ ─ (3 pieces not used)          │  │ ─ (3 pieces not used)          │
└─────────────────────────────────┘  └─────────────────────────────────┘
 + web-search row + cost row (existing spec 0031 treatment)
```

The cards sit BELOW the existing grid row (which spans columns 2-3 of
the 3-col grid; the row's phase-label cell in column 1 stays vertically
centred). Cards are 1:1 width using `grid-template-columns:1fr 1fr;
gap:14px`. Each card has:

- Header: `[icon] [agent name] · NNNk t (X.X% of cap)`.
- Total bar (full width, agent color, scale-relative).
- Divider (`1px solid var(--border-1)`).
- Sub-bar block: one row per non-zero piece, in current sort order
  (descending size by default; toggled via a small `sort` link at the
  card header).
- "(N pieces not used)" footnote when applicable, in muted mono.

A new `ConsumptionCard` component encapsulates this. A new
`SubInputBar` component renders one piece row (label + bar + token
count).

### 3. Sub-input color palette — `run-detail.jsx`

```js
// Spec 0035: distinct from agent colors (which stay on the TOTAL bar).
// Picked to be visually disambiguous from var(--agent-a) / var(--agent-b)
// and from each other under both light + dark themes.
const SUBINPUT_COLORS = {
  brief: '#5a7fc7',   // indigo
  d1:    '#a98a5a',   // ochre (NOT Claude orange)
  d2:    '#6f8c7a',   // sage (NOT GPT green)
  plan:  '#7a6b9a',   // plum
  hist:  '#c08570',   // rose
  draft: '#5d8a8a',   // teal
  histp: '#a18560',   // slate-amber
};
```

The COLLAPSED row's segmented bar keeps the existing `KIND_COLORS`
palette (per D5) — that compact view continues to read as "the same
chip palette as how-it-works". A code comment notes the dual
palette intentionally and explains why.

### 4. App-version chip in chrome — `app.jsx` + `live-data.jsx`

New helper in `live-data.jsx`:

```js
// Spec 0035: lazy-fetch /api/health on app mount; cache on window.__appMeta.
function useAppMeta() {
  const [meta, setMeta] = React.useState(window.__appMeta || null);
  React.useEffect(() => {
    if (window.__appMeta) return;
    authedFetch('/api/health')
      .then(r => r.json())
      .then(d => {
        window.__appMeta = d;
        setMeta(d);
      })
      .catch(() => {/* silent — chip just doesn't render */});
  }, []);
  return meta;
}
```

Exported via `Object.assign(window, ...)` (same pattern as
`useFileBody`, `useInputBundle`).

`ChromeBar` (`app.jsx:114`) adds a new `AppVersionChip` to its right
edge:

```jsx
function AppVersionChip({ meta, onClick }) {
  if (!meta?.version) return null;
  return (
    <button
      type="button"
      onClick={onClick}
      title={`dual-research v${meta.version} · click for release notes`}
      style={{
        appearance: 'none', border: '1px solid var(--border-1)',
        background: 'transparent', borderRadius: 999,
        padding: '2px 8px',
        fontFamily: 'var(--mono)', fontSize: 10.5,
        color: 'var(--fg-3)', cursor: 'pointer',
      }}
    >
      v{meta.version}
    </button>
  );
}
```

On click: navigates to `/how-it-works#version-notes` (the existing
VERSION_NOTES section on the how-it-works page) using the existing
`navigate` prop already passed to `ChromeBar`.

Positioned to the LEFT of the existing tabs / settings cluster on the
right end of the chrome bar.

### 5. Header rework — spec 0033 follow-up

Dismantles the four-row `RunDetailHeader` from spec 0033 and folds
its responsibilities into their natural homes (run header for chrome,
Timeline pane for per-agent + tab state).

`run-detail.jsx`:

- `RunDetailHeader` reverts to the two-row layout (the spec-0024 / pre-0033
  shape). Drops the `tab` / `onTabChange` props, the `<AgentStrip>` rows,
  and the inline `<TimelineTabs prominent>` render. Row 1 = topic + cost +
  status/errors badge. Row 2 = phase dots + dot labels + metadata
  (`started · drafter · elapsed · round`). The dot-labels strip + metadata
  line that lived in spec 0033's row 4 collapses to the existing single
  metadata row from pre-0033 (the dot-labels strip is preserved — it's
  small + useful — but inlines on the same row as the metadata).
- `AgentStrip` becomes a pill-shaped Timeline-toolbar component (replaces
  the full-row variant). Same content (icon · name · model · tokens·cost
  · pulse-dot · activity sentence) but laid out as a single-line inline-
  flex pill. Border becomes the agent's color (matches
  `AgentLegendChip`'s `meta.border`); no separate left-rail.
- `AgentLegendChip` is **deleted** — replaced by `AgentStrip` everywhere
  it was used (the Timeline `PaneToolbar`).
- `Timeline` re-owns its `tab` state internally (a `React.useState`
  inside the component, same as pre-spec-0033). `RunDetail` stops
  threading `timelineTab` / `setTimelineTab` props.
- The two header rows of the Timeline pane carry the new pills, one each:
  - **Row 1 — `PaneHeader`**: `Timeline · N artifacts` (existing) ... `[flex]` ... `[AgentStrip claude]`. The `PaneHeader` component gains a `right` slot for content like this (the props already accept a right-edge child — confirm in the existing API before adding).
  - **Row 2 — `PaneToolbar`**: `[AgentStrip gpt]` ... `[live-count chip]` ... `[flex]` ... `[TimelineTabs prominent]`. The two `AgentLegendChip`s that lived here are removed.
  The two pills end up vertically aligned on the right edge of consecutive rows. No `flex-wrap` is used; the layout reads identically at every viewport down to the practical pane minimum.

`app.jsx`:
- No change (the chrome bar's tab cluster is untouched). The version
  chip from §4 still lives in the global chrome.

### 6. Tests

Frontend rework is largely visual; the only meaningful unit-testable
bits are the helpers:

- `tests/protocol/test_blocks.py` — unchanged (spec 0034).
- New `tests/ui/test_server_health_version.py` — already in place
  via `_make_app`'s `/api/health`; extend the existing
  `tests/ui/test_server.py` if a version assertion is missing.
- Frontend: manual verification only.
  - Open Consumption tab on a fresh prod-tier run mid-Phase 2.
    Bars sized to data (~5–80K range), with a tick marker at the
    1M position labelled `1M`. Caption above: `scale: 87K · cap 1M`.
  - Click a row to expand. Two per-agent cards appear below the
    row, each with a total bar + stacked sub-bars in distinct
    non-agent colors. Sort defaults to descending size.
  - Toggle the "sort" link → flips to canonical Tk order.
  - Empty-piece footnote appears at the bottom of each card
    naming the unused Tk keys.
  - Chrome bar's right edge shows `v0.33.0` chip. Click → opens
    the how-it-works page, jumps to the version notes.
  - Hosted UI deploy — fetch `/api/health`; verify the chip
    renders the deployed version.

### 7. Files touched

Backend: none (other than docstring updates if the consumption-tab
caption strings reference module-level constants — unlikely).

Frontend:
- `src/dual_research/ui/static/run-detail.jsx`:
  - `computeConsumptionScale` added.
  - `ConsumptionView` threads `scale` into all bar renderers.
  - `ContextWindowMarker` added.
  - `ConsumptionRowExpanded` rewritten to render two per-agent cards.
  - `ConsumptionCard` + `SubInputBar` added.
  - `SUBINPUT_COLORS` map added (alongside the existing
    `KIND_COLORS` for the collapsed segmented view).
  - Scale caption above the grid.
  - **Header rework (§5)**: `RunDetailHeader` reverts to two rows
    (topic + cost + status; phase dots + meta). Drops the per-agent
    strip rows + the prominent tab pill. Drops the `tab` /
    `onTabChange` props.
  - **`AgentStrip` rewritten as a Timeline-toolbar pill** (replaces
    full-row variant + the deleted `AgentLegendChip`).
  - **`AgentLegendChip` deleted.**
  - `Timeline` re-owns its `tab` state internally; the
    `PaneToolbar` renders `[Claude strip] [GPT strip] [live chip]
    [flex] [Conversation/Consumption tabs]`.
- `src/dual_research/ui/static/live-data.jsx`:
  - `useAppMeta` hook added, window-exported.
- `src/dual_research/ui/static/app.jsx`:
  - `AppVersionChip` added; rendered in the right cluster of
    `ChromeBar`.

### 8. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.32.0 → 0.33.0.
- `CHANGELOG.md`: new `## [0.33.0] — YYYY-MM-DD` entry.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`.

## Out of scope

- **A log-scale toggle for the Consumption bars.** Data-relative
  linear scale (D1) was the user's explicit ask. A log option could
  be added if multi-order-of-magnitude runs become common.
- **Removing the segmented compact bar on the collapsed row.**
  Spec 0030's segmented compact view stays — it's the right shape
  for skimming round-over-round growth (D5).
- **Editing or rebalancing the per-piece breakdown from the UI.**
  Read-only.
- **A "compare runs side-by-side" Consumption view.** Single-run
  only, same as today.
- **Adding the version chip to the run-detail header itself.** The
  chrome bar is global; the run-detail header is run-specific
  (D9). Mixing them would clutter both.
- **A real-time SSE push of /api/health for live version flips
  during a session.** One-shot on mount is enough; users navigate
  between runs frequently enough that the chip will refresh on
  any full app reload.
- **Manual UI verification of specs 0033 + 0034 carried forward.**
  Still on the user's plate per spec 0034 wrap-up.
- **Reorganising the chrome bar's tab cluster.** Only the
  version chip is added; the existing `All runs / Help / Settings`
  arrangement stays. The version chip sits left of that cluster.
- **A scrollspy / sticky header inside the Timeline pane.** The
  new toolbar carrying both per-agent strips and tabs stays in
  document flow.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; no new backend tests
      are strictly required (the changes are visual and the data
      flow into the Consumption tab is unchanged).
- [ ] Manual: prod-tier Phase 2 round 3 → Consumption tab. Bars are
      legible (filled visually, not 1px slivers). Tick marker at
      1M position. Caption "scale: NNNk · cap 1M" above the grid.
- [ ] Manual: expand a row. Per-agent cards render. Sub-bars use
      the new SUBINPUT_COLORS palette — visibly distinct from the
      agent-colored total bar above them.
- [ ] Manual: sort toggle works; canonical-order swap is instant.
- [ ] Manual: (N pieces not used) footnote correctly names the
      Tk keys with zero token count.
- [ ] Manual: chrome bar shows `v0.33.0` chip. Click → how-it-works
      page, jumps to the version notes section.
- [ ] Manual: hosted UI — chip reflects the deployed version (not
      a stale bundled value).
- [ ] Manual: pre-0035 runs render with the new visual treatment
      (no data migration; the `prompt_pieces` field has been on the
      wire since spec 0030).
- [ ] Manual (header rework): run header is back to two rows —
      topic + cost + status on row 1; phase dots + dot labels +
      `started · drafter · elapsed · round` metadata on row 2. No
      tabs in the header, no per-agent strips.
- [ ] Manual (header rework): Timeline pane row 1 shows
      `Timeline · N artifacts` on the left and the Claude pill
      (`[icon] [name] [model] · [tokens·cost] │ [● phrase]`) on
      the right.
- [ ] Manual (header rework): Timeline pane row 2 shows the GPT
      pill on the left (same shape as the Claude pill), the
      live-count chip next to it, and the Conversation /
      Consumption tabs (prominent variant — accent underline on
      active) on the right.
- [ ] Manual (header rework): Claude pill (row 1) and GPT pill
      (row 2) align vertically on the right edge of their rows.
- [ ] Manual (header rework): the previous `AgentLegendChip`s
      are gone — no duplicate per-agent badges in the toolbar.
- [ ] Manual (header rework): pulse + status sentence on each
      pill behave identically to the spec-0033 strip (live during
      that agent's turn, grey/idle otherwise).

## Risks

- **Data-relative scale hides cap-relative variance between runs.**
  A run with 50K consumption and one with 500K both render at "full
  bar" because each is normalised to its own data. Mitigation: the
  caption + the cap marker both name the absolute scale, so the
  user can read "this run only ever consumed ~80K" at a glance.
- **`computeConsumptionScale` allocates every row on every render.**
  Tens of rows × 2 agents × 2 reads per agent = ~100 ops per render
  pass; trivial. Memoise via `React.useMemo` against `rows` to be
  safe.
- **`SUBINPUT_COLORS` clashes with the existing theme tokens.**
  Picked to be visually distinct from `var(--agent-a)` /
  `var(--agent-b)` but not theme-tokenised. Mitigation: they're
  literal hex strings; if any read poorly under the dark theme,
  swap to theme-aware tokens in a follow-up. Captured in Open
  questions.
- **`/api/health` returns stale version on the hosted UI if the
  client is cached.** First-visit users get the fresh value via
  the once-on-mount fetch; subsequent navigations within the same
  tab see the cached `window.__appMeta`. Mitigation: cache key is
  per-window, not persisted to localStorage; a hard reload always
  re-fetches.
- **Expanded-row layout breaks at narrow widths.** Two side-by-side
  cards × ~340px minimum × 14px gap × the grid's 120px label
  column = ~810px before the row stops fitting comfortably. The
  Consumption tab lives in a half-pane (the right half being the
  Critique explorer), so the practical floor is ~640px which is
  fine for desktop. On a 1280px viewport with explorer collapsed
  the cards have plenty of room. Mitigation: a `min-width: 0` on
  each card + horizontal overflow on the inner sub-bar block.
- **The "(N pieces not used)" footnote naming Tk keys directly
  (`brief / d1 / d2 …`) is jargon for first-time viewers.** Use
  the friendly labels from `INPUT_PIECE_LABEL` (spec 0033) — they
  already exist, are user-facing, and read as English.
- **Header rework removes the live activity sentence from the top
  chrome.** It moves down into the Timeline pane toolbar, where
  it lives on the per-agent pill. The signal isn't lost — just
  rehomed. Acceptable per the user's explicit redirect.
- **`AgentLegendChip` is referenced by name in any external
  bookmark / handoff doc** (none known). Internal-only deletion;
  no migration. Captured for completeness.
- **Row 1 (`PaneHeader`) doesn't natively support right-edge
  content** beyond what the existing `right` prop carries. If
  the `PaneHeader` API doesn't accept arbitrary nodes, the Claude
  pill won't render in line with the title. Mitigation:
  `PaneHeader` already takes a `right` slot (the spec-0014
  `SmallStat` pair on the Critique explorer renders through
  it) — passing an `<AgentStrip>` node should work without
  changes. Verify before writing the JSX; extend the component
  if needed.
- **Single-row pills on row 1 + row 2 may push the row beyond
  the pane width** at very narrow viewports (≤ 640px). The
  Conversation tab + pill + meta could collide. Mitigation:
  the pane sits in a half-screen split of the main view; the
  practical floor is ~700px which the layout absorbs. The
  pill's model id truncates with ellipsis if needed.

## Open questions

- Whether the **app-version chip** should also surface in the
  bottom-right of the page (footer) for users on the
  per-run-detail view where the chrome bar is visually distant.
  v1 sticks to chrome only — keeping one source of truth is
  cleaner. Easy to add a second placement if requested.
- Whether `SUBINPUT_COLORS` should be **CSS custom properties**
  in `theme.css` rather than inline hex. Trades flexibility for
  one more layer of indirection; v1 keeps hex literals next to
  the consumer for legibility. Theme-toggle hot-swap is a
  future spec if needed.
- Whether the **sort toggle on each card** should persist across
  the open/close cycle within the same run. v1 doesn't (each
  card opens with descending-size); future spec could persist
  per-card-id in `window.__consumptionSort` if it feels needed.
- Whether **clicking the version chip** should pop a small
  inline panel with the most recent VERSION_NOTES entry instead
  of navigating to how-it-works. Inline pop is heavier; v1
  picks the navigate path. Could iterate.
- Whether to **animate** the sub-bar appearance on row expand
  (slide-down). Today's row expand is instant; matching is
  consistent. Could add a 200ms ease-out if it feels abrupt.
