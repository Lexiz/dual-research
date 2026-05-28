---
kind: dev
spec: "0246"
slug: all-runs-card-layout-rewrite
title: All Runs landing page — card layout rewrite + summary stats panel
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.60.0
status: queued
depends_on: []
complexity: L
created: 2026-05-28
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "User-requested visual rewrite of the project's primary landing page — first surface every signed-in user lands on; replaces the existing run-list React tree (no .runs-* classes, all inline styles) with a card-based layout per pixel-perfect design handoff."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0246 — All Runs landing page — card layout rewrite + summary stats panel

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** —
> **Bump:** MINOR — new landing-page composition + new composed components + additive API fields; no breaking contract.
> **Evidence:** Design handoff bundle authored in conversation prior to queueing — `All Runs.html` (1527 lines, hi-fi pixel-perfect mock) + `README.md` (33 KB written-out anatomy) + `styles/v2-m3.css` (no new tokens; cite the existing DS). The mock was rendered locally with light/dark toggle wired at `http://127.0.0.1:7777/` for visual review before this spec was queued. The bundle lives under `~/Downloads/design_handoff_all_runs/`; it is the canonical visual contract for this spec but is not checked into the repo — the spec body below transcribes every load-bearing measurement, token, and state from it so the spec stands on its own.

---

## 1. Context

The current All Runs page at [src/dual_research/ui/static/run-list.jsx:98-511](src/dual_research/ui/static/run-list.jsx#L98) is a React component that renders a sparse table-ish list: each row shows status, topic, started/duration/rounds/cost in a flat layout with **no dedicated CSS classes** — every visual property is set inline via React `style=` props on top of a shared design-token vocabulary. The page also embeds an inline search input (run-list.jsx:143–155 — focus-on-`/` keyboard shortcut) and a single tab-group of filter chips. There is no aggregate view: a user landing on the page cannot see at a glance how many runs are stalled, what compute is being burned on dead runs, or where most runs are getting stuck. On a large monitor the layout wastes most of the horizontal real estate. There is also no test coverage at all for the page anatomy — `tests/ui/test_server_cache.py:452,483` exercises the `/api/runs` endpoint but not the surface.

The redesign moves to a card-based layout with a summary stats panel at the top, status-grouped sections (Needs attention / Converged / Running), and per-run cards that surface phase outcomes, per-agent cost split, and the failure or completion reason. The motivation is operational: the project's primary landing page should answer "where is my time and money going?" without a click. The full anatomy — measurements, tokens, states, motion, accessibility — is transcribed below from the handoff bundle. The page must render pixel-faithfully under the existing dual-research design system v2 (`design-system/SPEC.md`, [design-system/assets/styles/tokens-and-primitives.css](design-system/assets/styles/tokens-and-primitives.css)) using only existing tokens (no new color/spacing/font definitions) and must add the five new composed components the layout needs.

### 1.1 — Source-handoff traceability

Every atomic visual element in the handoff bundle lands somewhere in this spec. The table below pins each element to the §2.N subsection that ships it, or to §5 with a named follow-up.

| source item | source quote/ref | spec section |
|---|---|---|
| Top chrome (60 px sticky) — All runs / Compare / Search tabs, connection pill, version pill, How it works, theme toggle, avatar | `All Runs.html:662-682` | §2.2 |
| Project strip — overlapping circles mark + `dual-research` name | `All Runs.html:687-694` | §2.3 |
| Stats panel — 5 tiles in `1fr 1fr 1fr 1fr 1.5fr` grid: Total spend, Convergence rate, Avg cost / run, Avg duration, Where runs ended | `All Runs.html:697-742` | §2.4 |
| Phase distribution chart (tile 5 — P1..P5 stacked bars sized by `count / max_count * 100`) | `All Runs.html:720-740` | §2.4 |
| Filter chip row — All / Running / Converged / Deadlocked / Errored / Abandoned / Completed + Sort | `All Runs.html:745-757` | §2.5 |
| Group section header — icon + title + count badge + hint (warn-tinted for Needs attention; default for Converged) | `All Runs.html:760-766, 1462-1467` | §2.6 |
| Run card grid container | `All Runs.html:768-769` | §2.7 |
| Run card composed component — grid `head / phases agents / note`, 3 px status accent stripe, errored radial decoration | `All Runs.html:771-818` (and 14 further variants 820-1519) | §2.8 |
| 5-segment phase strip with `done / active / failed / abandon / pending` states + shimmer + diagonal-stripe pattern | `All Runs.html:795-801, 524-543` | §2.8.5 |
| Per-agent row (Claude on sable accent / GPT on sage accent — cost + chip tags) | `All Runs.html:802-813, 311-366` | §2.8.6 |
| Note row variants (err / warn / ok) with leading Material Symbols icon | `All Runs.html:814-817, 546-562` | §2.8.7 |
| Light theme toggle — `body.light` class switch persisted to `localStorage` | Mock wires the existing `contrast` button to `body.classList.toggle('light')` (added in `index.html`) | §2.9 |
| Responsive breakpoints — 1180 px (stats collapse to 3 cols), 760 px (stats collapse to 2 cols, page padding shrinks) | `All Runs.html:640-655` | §2.10 |
| 15-run canonical fixture (14 needs-attention + 1 converged) — drives source-pattern tests | `README.md` "Run data" table | §6 |
| "Drift" / "Conceded" / "Scope flip" / "Ctx overflow" / "Runaway review loop" semantic chip kinds | `README.md` chip table footnote | §5 (deferred to spec NNNN — semantic derivation needs LLM-or-heuristic analysis, out of scope here) |
| `.rc-phase--active` shimmer + `.run-card--running` info-tinted accent stripe | `All Runs.html:527-534, 442-445` | §2.8 (rendered when `status: running` data flows in; surface lands now, derivation lands now) |
| "New run" entry-point CTA card | `All Runs.html:597-638` | §5 (out of scope — README §"Out-of-scope notes" line 608 explicitly states the new-run entry point lives in existing chrome) |
| Empty state when filter yields zero results | README §"Empty state" line 451 | §5 (out of scope — reuse existing empty-state pattern at first-render; design follow-up if needed) |
| Density toggle (`body.compact`) | README line 449 | §5 (out of scope — exists in DS, not part of this rebuild) |

---

## 2. Proposed change

The change has nine sub-parts: the existing implementation is removed in 2.1, then the new page is built up component by component (2.2–2.10). Every visual measurement comes from the transcribed `All Runs.html` source (cited at the §1.1 line numbers).

The CSS class vocabulary from the handoff is preserved **verbatim** — the spec adopts `.ar-*` (all-runs page-level) and `.rc-*` (run-card-level) prefixes as authored, both in [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css) (authoritative) and in the live-app mirror at [src/dual_research/ui/static/components.css](src/dual_research/ui/static/components.css). Per the project rule, both files MUST be updated in the same commit.

### 2.1 — Remove the current implementation

The current React tree at [src/dual_research/ui/static/run-list.jsx:98-511](src/dual_research/ui/static/run-list.jsx#L98) is deleted in full. Specifically:

- `RunListView({ runs, loading, onSelect })` at run-list.jsx:98 — replaced by `AllRunsPage({ runs, loading, onSelect })` (new function in the same file).
- `RunRow({ run, onSelect, attentionSummary, tourAnchor })` at run-list.jsx:413 — replaced by `<RunCard run={...} onSelect={...} />` (new function in the same file).
- `PhaseMini({ phase, status })` at run-list.jsx:489 — **kept** for cross-surface use (also used in run-detail timeline cards); the new All Runs page does **not** consume it (it has its own `<PhaseStrip />` composed component, §2.8.5). The shared primitive stays in place for the run-detail consumer.
- The inline `/`-focus keyboard handler at run-list.jsx:143–155 is removed (no inline search on the new page — see §5).
- The `?q=` query-param state at [src/dual_research/ui/static/router.jsx:6-23](src/dual_research/ui/static/router.jsx#L6) is **no-op'd on the All Runs page** — the param parser remains for backward compatibility but the page does not read it. `?sort=` and `?filter=` remain functional.
- All inline `style={{ ... }}` expressions inside the deleted run-list components go away; the new tree uses class names from the new composed components.

### 2.2 — Top chrome (`.ar-chrome`)

Replaces the existing chrome bar on the All Runs route only. The chrome layout matches `All Runs.html:662-682` verbatim:

- 60 px tall sticky bar, `z-index: 30`, background `--md-surface-container`, bottom border `1px solid var(--md-outline-hair)`, padding `0 20px`, flex row centered.
- **Tab cluster** (left): three tabs in a `.ar-chrome__tabs` flex row — `All runs` (active, `aria-current="page"`), `Compare`, `Search`. Each tab is `.ar-tab` (36 px, 16 px h-padding, fully rounded, M3 secondary-container tonal on active). Material Symbols icons at 18 px (`view_agenda`, `compare_arrows`, `search`) precede each label.
- **Spacer** (`.ar-chrome__sp`) flexes to push the right cluster.
- **Connection pill** (`.ar-pill` with a `.dot.dot--ok` 6 px green dot at `--p-ok` plus a 3 px soft glow): `● connected`. 28 px tall, outlined.
- **Version pill** (`.ar-pill` with `.ar-pill__v` 11 px mono interior): `v1.58.1`. Reads the version from `pyproject.toml` injected at page render — same source as today's chrome.
- **How it works** tab (`.ar-tab`).
- **Theme toggle** (`.md-icon-btn` with `contrast` Material Symbol, 20 px) — toggles `body.light` class, persisted to `localStorage` key `dr-theme`.
- **Avatar** (`.ar-avatar` 34×34 circle, `linear-gradient(135deg, var(--p-sable), var(--p-sage))`, initial letter `a` centered, weight 500).

DS citation: existing `.md-appbar` tonal vocabulary per [design-system/SPEC.md §2.2 Surfaces](design-system/SPEC.md#22--surfaces-m3-tonal-scale) + state-layer overlay per [§2.10 State layers](design-system/SPEC.md#210--state-layers). The chrome wrapper `.ar-chrome` is a **new composed component** — it is a project-strip-aware sticky shell that the existing `.md-appbar` primitive does not cover. Add to composed-components.css under "All Runs page chrome" with a comment pointer back to this spec.

### 2.3 — Project strip (`.ar-project`)

Single row, 28 px bottom margin (`All Runs.html:687-694`). Contents:

- 22 × 22 brand mark (`.ar-project__mark`): two overlapping 12 × 12 circles (left = `--p-sable`, right = `--p-sage`) with `mix-blend-mode: screen`. Drawn purely in CSS — no asset.
- Project name `.ar-project__name`: 18 px, weight 500, letter-spacing `-0.005em`, color `--md-on-surface`. Text: `dual-research` (static — single project app).

DS citation: brand-identity treatment per [design-system/SPEC.md §2.12 Icons](design-system/SPEC.md#212--icons) (existing BrandMark pattern). The `.ar-project` shell is new; the inner mark is the existing brand mark.

### 2.4 — Stats panel (`.ar-stats`)

CSS grid `grid-template-columns: 1fr 1fr 1fr 1fr 1.5fr` (the last tile is 1.5× wider for the phase chart). 1 px gap with `--md-outline-hair` as the gutter background, 1 px outer border in the same token, 16 px border-radius (`--md-shape-lg`), `overflow: hidden`. 24 px bottom margin. Each tile (`.ar-stat`): `padding: 14px 18px`, `min-height: 104px`, flex column with `justify-content: space-between`.

Per-tile children:

- `.ar-stat__label` — 10 px, weight 500, uppercase, 0.1em tracking, color `--md-on-surface-faint`.
- `.ar-stat__value` — 26 px, weight regular, font family `--md-font-brand` (Roboto Serif), `-0.015em` letter-spacing, `font-feature-settings: "tnum","ss01"`.
- `.ar-stat__hint` — 11 px, color `--md-on-surface-variant`, line-height 1.4. `<b>` children: weight 500, `--md-on-surface`. `.neg`: `--p-err`. `.pos`: `--p-ok`.

The five tiles, in order (computed client-side from the loaded run list):

1. **Total spend** — sum of `run.cost` across all runs. Format `$N.NN`. Hint: `<b>$X</b> on stalled runs · <b>$Y</b> converged` where stalled = errored + abandoned + deadlocked, converged = completed.
2. **Convergence rate** — `completed / total * 100`, format `N.N%`. Hint: `<b>{total} runs</b> · <b>{completed} converged</b>`.
3. **Avg cost / run** — `total_spend / total`, format `$N.NN`. Hint: `Range <b>$min</b> – <b>$max</b>`.
4. **Avg duration** — mean over runs with `duration > 0`, format `mm:ss` or `Nh NNm`. Hint: `Excludes runs abandoned at P2 ({count})` where count = runs whose final phase is P2 with abandoned status.
5. **Where runs ended** (`.ar-stat.ar-stat--phase`) — the phase distribution chart described below.

#### 2.4.1 Phase distribution chart (`.phase-dist`)

3-column subgrid `28px 1fr 28px`, gap `6px 10px`, vertically centered. One row per phase P1–P5: `[code] [bar] [count]`.

- `.phase-dist__code` — 11 px mono (`--md-font-data`), `--md-on-surface-faint`, 0.04em tracking. Text: `P1`..`P5`.
- `.phase-dist__bar` — 8 px tall, 2 px radius, background `--md-outline-hair`.
- `.phase-dist__fill` — inner div, `width: <pct>%`, where `pct = count(phase) / max(count) * 100`. Default fill `--p-warn`. Modifiers: `.--ok` → `--p-ok`, `.--err` → `--p-err`, `.--mix` → `linear-gradient(90deg, var(--p-warn) 0%, var(--p-warn) 60%, var(--p-err) 60%, var(--p-err) 100%)`.
- `.phase-dist__count` — 11 px mono, right-aligned, tabular nums.

Fill kind by phase: phases that end in `abandon` use default warn; phases that end in `failed` use err; pure success (P5 reached) uses ok; mixed (some failed + some warn in the same phase bucket) uses `--mix`. Aggregation key per run = the phase at which the run's terminal state landed (e.g. P4 errored = bucket P4 with kind err).

`.stats-grid` + `.stats-tile` + `.phase-dist` are **new composed components** in composed-components.css. DS citation: [design-system/SPEC.md §3](design-system/SPEC.md#3--primitives) (Card primitive) for tile containers, [§2.5 Typography](design-system/SPEC.md#25--typography) for the type scale.

### 2.5 — Filter chip row (`.ar-filters`)

Flex row, 8 px gap, `flex-wrap: wrap`, 20 px bottom margin. Seven filter chips followed by a `.ar-filters__sp` flexible spacer and a `.ar-sort` sort affordance.

`.fchip` — 32 px tall, 14 px h-padding, fully rounded:

- Default: transparent background, `inset 0 0 0 1px var(--md-outline-variant)` border, color `--md-on-surface-variant`, font 12 px / weight 500 / 0.04em tracking.
- `aria-pressed="true"` (active): background `--md-secondary-container`, color `--md-on-secondary-container`, no border.
- Hover: pseudo-overlay at `--md-state-hover` opacity (0.08).
- Children: optional `.swatch` (8 px circle in status color — `--running`, `--converged`, `--deadlocked`, `--errored`, `--abandoned`, `--completed`), label, and `.ct` count separator (4 px left padding, 1 px left border in `--md-outline-variant`, 11 px mono `--md-font-data`).

Seven chips, in order, with single-select semantics (parity with current page):

| Chip | Default state | Swatch token | Counts |
|---|---|---|---|
| All | `aria-pressed="true"` | — | total |
| Running | inactive | `--p-info` | `count(status="running")` |
| Converged | inactive | `--p-ok` | `count(status="converged")` |
| Deadlocked | inactive | `--p-warn` | `count(status="deadlocked")` |
| Errored | inactive | `--p-err` | `count(status="errored")` |
| Abandoned | inactive | `--p-warn` | `count(status="abandoned")` |
| Completed | inactive | `--p-ok` | `count(status="completed")` |

Click toggles the `?filter=<status>` URL state (same query param the router already uses at [src/dual_research/ui/static/router.jsx:6-23](src/dual_research/ui/static/router.jsx#L6)); the visible group sections (§2.6) re-filter on the new state.

`.ar-sort` is the existing sort affordance — same vocabulary as today (`?sort=started:desc`, `?sort=cost:desc`, `?sort=duration:desc`, `?sort=id:asc`), restyled to match the chip vocabulary: 32 px tall, 12 px h-padding, fully rounded, leading `sort` Material Symbol icon at 18 px, label `Started, newest` (or the current sort's human label).

DS citation: existing `.md-chip` per [design-system/SPEC.md §3](design-system/SPEC.md#3--primitives) and the count-chip pattern from [§4.1 Critique pane](design-system/SPEC.md#41--critique-pane) (where `chip-value` spans are precedent for the right-aligned count). `.fchip` is added as a thin restyle in composed-components.css — same primitive, different padding + the swatch dot.

### 2.6 — Section group headers (`.ar-group`, `.ar-group__head`)

Runs are partitioned into three groups, in this top-down order:

1. **Running** (`.ar-group`) — present only if any run has `status=running`. Title `Running`, neutral tone, icon `play_circle` in `--p-info`. Hint: `<count> in flight · $<spend> spent so far`.
2. **Needs attention** (`.ar-group.ar-group--warn`) — present if any run has `status ∈ {errored, abandoned, deadlocked}`. Title `Needs attention` (in `--p-warn`), icon `warning_amber` (in `--p-warn`). Hint: `$<stalled_spend> of compute on stalled runs · <P2_count> abandoned in P2 (plan negotiation)` — computed from the partition.
3. **Converged** (`.ar-group`) — present if any run has `status ∈ {completed, converged}`. Title `Converged`, icon `check_circle` in `--p-ok`. Hint: `Clean P5 finish · $<avg> average · <avg_dur> average`.

Group header (`.ar-group__head`):

- Flex row, 12 px gap, 14 px bottom margin, 12 px bottom padding, `border-bottom: 1px solid var(--md-outline-hair)`.
- Leading icon (`.ic`, Material Symbols 20 px).
- `.ar-group__title` — 13 px, weight 500, uppercase, 0.08em tracking.
- `.ar-group__count` — 11 px mono, padded 4×8, fully rounded, background `--md-surface-container`.
- `.ar-group__hint` — `margin-left: auto`, 12 px, `--md-on-surface-faint`.

When a filter chip is active (anything other than `All`), only the group containing that status is rendered.

Group top margin: 36 px (`.ar-group { margin-top: 36px }`); first group only gets 8 px.

`.ar-group` is a **new composed component**. DS citation: section-header pattern adapts the [§4.1 Critique pane](design-system/SPEC.md#41--critique-pane) collapsible-section chevron treatment but with a fixed (non-collapsing) form — the section is always expanded on the All Runs page.

### 2.7 — Card grid (`.ar-grid`)

`display: grid; grid-template-columns: 1fr; gap: 12px;`. Single column, full-width cards (the rich card layout already uses internal grid columns; no need for a multi-column outer grid even on wide monitors).

### 2.8 — Run card (`.run-card`) — the primary composed component

The run card is the focal element. Each card represents one run; click anywhere on the card navigates to that run's detail view via the existing `onSelect(runId)` prop (no route change in this spec).

#### 2.8.1 Container shell

```css
.run-card {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto auto;
  grid-template-areas:
    "head    head"
    "phases  agents"
    "note    note";
  column-gap: 32px;
  row-gap: 12px;
  align-items: center;
  padding: 12px 18px 14px 22px;
  background: var(--md-surface-container-low);
  border: 1px solid var(--md-outline-hair);
  border-radius: var(--md-shape-md);
  cursor: pointer;
  overflow: hidden;
  transition: background var(--md-dur-short-3) var(--md-easing-standard),
              border-color var(--md-dur-short-3) var(--md-easing-standard),
              transform var(--md-dur-short-3) var(--md-easing-standard);
}
```

- **3 px left accent stripe** via `::before`, full card height, color = status color (`--p-err` errored, `--p-warn` abandoned, `--p-ok` completed, `--p-info` running). The left padding is `22px` (vs. `18px` right) specifically to clear this stripe.
- **Errored decorative `::after`**: radial gradient `420px 140px at 0% 0%, color-mix(in srgb, var(--p-err) 8%, transparent), transparent 70%`, `pointer-events: none`.
- **Running decorative `::after`**: same radial gradient but at 10% `--p-info` mix.
- **Completed** cards: `background: var(--md-surface-1)` (slightly elevated tone).
- **Hover**: background → `--md-surface-1`, border → `--md-outline-variant`, `transform: translateY(-1px)`. Transition 150 ms (`--md-dur-short-3`) M3 standard easing.

Grid areas — three rows, two columns:

- Row 1 `head` (full width) — flex container for status pill + topic + metrics + id badge.
- Row 2 `phases | agents` — two equal columns: phase strip left, agent rows right.
- Row 3 `note` (full width) — failure or completion explanation.

#### 2.8.2 Head row (`.rc-head`)

Flex row, `align-items: center`, `gap: 14px`. Contains, in order:

1. **Status pill** (`.rc-status`): 22 px tall, padding `0 10px`, fully rounded; font 10 px / weight 500 / uppercase / 0.08em tracking. Leading 5 px dot via `::before` in `currentColor`. Tonal variant per status: `.rc-status--errored` (text + dot `--p-err`, background `color-mix(in srgb, var(--p-err) 16%, transparent)`); same shape for `--abandoned` (`--p-warn`), `--completed` (`--p-ok`), `--running` (`--p-info`).
2. **Topic** (`.rc-topic`): `flex: 1; min-width: 0;` (claims remaining space); 14 px / weight 500 / line-height 1.3, color `--md-on-surface`; **single line** truncation: `white-space: nowrap; overflow: hidden; text-overflow: ellipsis;`.
3. **Metrics group** (`.rc-foot` nested inside `.rc-head`, `margin-left: auto`): flex row, 22 px gap, `align-items: flex-end`. Four `.rc-meta` cells: **Started**, **Duration**, **Rounds**, **Cost**. Each cell is a flex column with 3 px gap; label `.rc-meta__l` (9 px / weight 500 / uppercase / 0.08em / `--md-on-surface-faint`); value `.rc-meta__v` (12 px / weight 500 / `--md-font-data` / `font-variant-numeric: tabular-nums` / `white-space: nowrap` / `--md-on-surface`).
4. **ID badge** (`.rc-idbdg`): `flex: 0 0 auto`, 11 px mono / weight 500 / 0.04em tracking, padding `6px 10px`, fully rounded, background `--md-surface-container`, color `--md-on-surface-variant`, `inset 0 0 0 1px var(--md-outline-hair)`, `white-space: nowrap`. Format: full run id, `r-<8-hex>-<4-hex>` (the existing run-id format).

Value formats:

- **Started**: `"MMM DD, HH:MM"` (e.g. `May 28, 14:00`) — derived from `run.started_at` ISO.
- **Duration**: `mm:ss` for ≤ 59 min 59 s; `Nh NNm` for ≥ 1 h; `0:00` for never-started runs.
- **Rounds**: `n / 6` (existing `rounds: {completed, max}`).
- **Cost**: `$N.NN` — always 2 decimals.

#### 2.8.3 Hover chevron (`.rc-chev`)

A `chevron_right` icon at top-right (`position: absolute; top: 12px; right: 12px; width: 22px; height: 22px`), opacity 0 by default, 1 on `.run-card:hover` with 150 ms transition. Decorative only (`pointer-events: none`).

#### 2.8.4 Running ticker (`.rc-live`)

For `status=running` cards only: 8 px pulsing info dot at `position: absolute; top: 14px; right: 14px`, `box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-info) 28%, transparent)`, animated via the shared `@keyframes pulse` (`box-shadow` modulation, 1.8 s ease-in-out infinite). Replaces the hover chevron when active.

#### 2.8.5 Phase strip (`.rc-phases`)

Left half of row 2. `display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px`. Five `.rc-phase` cells (P1–P5), each a flex column with 3 px gap:

- `.rc-phase__bar` — 4 px tall, 2 px radius, default `--md-outline-hair`.
- `.rc-phase__lbl` — 9 px / weight 500 / `--md-font-data` / 0.04em tracking / `--md-on-surface-faint`. Text per cell: `P1 plan`, `P2 nego`, `P3 res`, `P4 rev`, `P5 sum`.

Phase state modifiers (one per cell based on `run.phases[i]`):

| Modifier | Bar | Label color |
|---|---|---|
| `.rc-phase--done` | solid `--p-sage` | `--md-on-surface-variant` |
| `.rc-phase--active` | solid `--p-info` + animated `::after` shimmer overlay (linear gradient, 2.4 s linear infinite, `@keyframes shimmer`) | `--p-info` |
| `.rc-phase--failed` | solid `--p-err` | `--p-err` |
| `.rc-phase--abandon` | `--p-warn` background + 45° diagonal-stripe pattern (`linear-gradient(45deg, transparent 25%, color-mix(in srgb, #000 18%, transparent) 25%, ...)`; `background-size: 6px 6px`) | `--p-warn` |
| `.rc-phase--pending` | default outline-hair bar | `--md-on-surface-decor` |

Phase computation per run: derive the `[Phase, Phase, Phase, Phase, Phase]` tuple server-side from existing per-turn artifacts (each turn carries the phase it executed in). Algorithm:

- For each phase Px (1..5): if any turn ran in this phase AND the run subsequently moved past it → `done`.
- The phase where the run terminated: `failed` if `status=errored`, `abandon` if `status=abandoned` or `status=deadlocked`, `active` if `status=running`.
- All later phases: `pending`.
- `status=completed`: all five phases `done`.

The new `phases` array on `RunListRow` (see §4) lets the front-end render this without re-deriving from raw turns.

`.run-phase-strip` / `.rc-phases` is a **new composed component** — a 5-segment variant of the existing 8-segment `.phase-progress` admin pattern at [design-system/SPEC.md §5.3](design-system/SPEC.md#53--admin--settings--progresssegs). The 5-segment shape is run-list-specific; keep it as `.rc-phases` (run-card-scoped) rather than promoting to a top-level primitive.

#### 2.8.6 Per-agent rows (`.rc-agents`, `.rc-agent`)

Right half of row 2. Flex column, 4 px gap. Two rows: Claude (`.rc-agent.rc-agent--a`) on top, GPT (`.rc-agent.rc-agent--b`) below.

```css
.rc-agent {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 10px 4px 12px;
  border-radius: var(--md-shape-sm);
  background: var(--md-surface-container);
  overflow: hidden;
}
```

2 px left accent stripe via `::before`: `--p-sable` for Claude, `--p-sage` for GPT (matches the existing agent-color convention at [design-system/SPEC.md §2.1 Palette](design-system/SPEC.md#21--palette)).

Children:

- `.rc-agent__name` — 10 px / weight 500 / uppercase / 0.06em tracking / `min-width: 50px`. Claude: `color-mix(in srgb, var(--p-sable) 90%, white)`. GPT: `color-mix(in srgb, var(--p-sage) 90%, white)`.
- `.rc-agent__cost` — 12 px / weight 500 / `--md-font-data` / tabular nums / `min-width: 50px` / `--md-on-surface`. Format `$N.NN`.
- `.rc-agent__chips` — flex row, 4 px gap, `margin-left: auto`.

Chip primitive (`.rc-bdg`):

```css
.rc-bdg {
  display: inline-flex; align-items: center; gap: 4px;
  height: 16px; padding: 0 6px;
  border-radius: var(--md-shape-full);
  font: 500 9px/1 var(--md-font-plain);
  letter-spacing: 0.04em;
  background: color-mix(in srgb, var(--md-on-surface) 8%, transparent);
  color: var(--md-on-surface-variant);
  white-space: nowrap;
}
.rc-bdg--warn { color: var(--p-warn); background: color-mix(in srgb, var(--p-warn) 16%, transparent); }
.rc-bdg--err  { color: var(--p-err);  background: color-mix(in srgb, var(--p-err) 16%, transparent); }
.rc-bdg--ok   { color: var(--p-ok);   background: color-mix(in srgb, var(--p-ok) 16%, transparent); }
.rc-bdg--info { color: var(--p-info); background: color-mix(in srgb, var(--p-info) 16%, transparent); }
```

The agent's `chips: Chip[]` array (see §4 schema) renders verbatim. Chip kinds that ship with derivation in this spec:

- `<N> plan turns` (neutral) — count of P1+P2 turns by this agent.
- `<N> critiques` (warn if N≥5, else neutral) — count of P4 critique turns by this agent.
- `<N> sources` (info) — count of distinct sources cited by this agent across the run.

Chip kinds whose derivation defers — see §5 — but whose rendering vocabulary lands now: `<N> conceded`, `<N> drift`, `scope flip`, `ctx overflow`, `runaway review loop`. The chip primitive is fully defined; the *content* fills in once the derivation specs ship. Until then those chips simply don't appear in the chip array.

`.rc-agent` is a **new composed component** — a compact variant of the [§4.3 Consumption row](design-system/SPEC.md#43--consumption-row) pattern. Use `--density: 1` (compact) tokens for the inner type scale.

#### 2.8.7 Note row (`.rc-note`)

Row 3, full width. Single-line explanation of the run's terminal state.

```css
.rc-note {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 7px 10px;
  border-radius: var(--md-shape-sm);
  background: var(--md-surface-container);
  color: var(--md-on-surface-variant);
  font: 400 11px/1.4 var(--md-font-plain);
}
```

Tonal variants:

- `.rc-note--err` — background `color-mix(in srgb, var(--p-err) 10%, var(--md-surface-container-low))`; text `color-mix(in srgb, var(--p-err) 60%, var(--md-on-surface-variant))`; icon `--p-err`; bold text `color-mix(in srgb, var(--p-err) 80%, white)`.
- `.rc-note--warn` — background `color-mix(in srgb, var(--p-warn) 8%, var(--md-surface-container-low))`; icon `--p-warn`.
- `.rc-note--ok` — background `color-mix(in srgb, var(--p-ok) 8%, var(--md-surface-container-low))`; icon `--p-ok`.

Leading Material Symbols `.ic` icon (16 px), `flex: 0 0 auto`:

- `error` — errored runs.
- `pause_circle` — manually-stopped (abandoned) runs.
- `timer_off` — errored runs whose terminal cause was a timeout / runaway loop (derivation: P4 elapsed > 2× the median P4 duration — heuristic, lands in this spec).
- `check_circle` — completed runs.

Note text source: derived server-side from existing run metadata (`status`, terminal `phase`, and the `stopping_reason` field in `meta.json` where present). Specifically:

- `status=completed` → `"Converged in <rounds> rounds. <critique_total> critiques resolved · 0 drift · ready to ship."` (where `0 drift` is the literal string until §5 derivation ships).
- `status=errored` with cause-of-death `timeout` → `"Runaway review loop · <minutes> min on review (<hours>h) before timeout."`
- `status=errored` with cause `context_overflow` → `"<Agent> context overflow · review round <N>, response truncated mid-critique."`
- `status=errored` other → `"<Agent> critique loop diverged. <rounds> rounds; no convergence on <P>."` — terminal `P` is the phase code.
- `status=abandoned` from P2 (plan negotiation) → `"Manually stopped <subphase>. <reason or empty>."`
- `status=abandoned` from later phases → `"Manually stopped in <phase>. <reason or empty>."`

Bold `<b>` runs use `--md-on-surface` and weight 500 (or per the err/warn/ok tonal modifier).

### 2.9 — Theme toggle

The `contrast` icon button in the chrome (§2.2) toggles `body.classList.toggle('light')` and persists the choice to `localStorage['dr-theme']`. The token set in [design-system/assets/styles/tokens-and-primitives.css](design-system/assets/styles/tokens-and-primitives.css) already defines both dark (default at `:root`) and `body.light` palettes — no token changes needed; all the new composed components automatically swap.

DS citation: [design-system/SPEC.md §6 Themes](design-system/SPEC.md#6--themes-dark--light).

### 2.10 — Responsive

- ≥ 1180 px (default): stats panel 5 columns, run cards full-width single column.
- 760 px to 1180 px: stats panel collapses to 3 columns; `.ar-stat--phase` spans 3 columns and drops its 104 px min-height. Run cards reduce side padding (`padding: 10px 14px 12px 18px; column-gap: 16px;`).
- < 760 px: page padding drops to `20px 16px 60px`; stats panel collapses to 2 columns; `.ar-stat--phase` spans 2; cards stay single column.

DS citation: [design-system/SPEC.md §7.2 Responsiveness — three breakpoints](design-system/SPEC.md#72--responsiveness--three-breakpoints). The breakpoint vocabulary already exists; this spec uses it.

### 2.11 — JSX composition

The new tree replaces [src/dual_research/ui/static/run-list.jsx:98-511](src/dual_research/ui/static/run-list.jsx#L98). Component skeleton (function signatures load-bearing; internal markup uses the new class names from §2.2–2.8):

```jsx
function AllRunsPage({ runs, loading, onSelect }) {
  const filter = useFilterFromUrl();       // existing router.jsx hook
  const sort = useSortFromUrl();
  const visibleRuns = applyFilterAndSort(runs, filter, sort);
  const groups = partitionByStatus(visibleRuns); // {running, attention, converged}
  const stats = computeStats(runs);              // aggregates over UNFILTERED runs

  return (
    <>
      <AllRunsChrome />
      <main className="ar-page">
        <ProjectStrip />
        <StatsPanel stats={stats} />
        <FilterChipRow filter={filter} counts={statusCounts(runs)} sort={sort} />
        {groups.running.length > 0 && <RunGroup kind="running" runs={groups.running} onSelect={onSelect} />}
        {groups.attention.length > 0 && <RunGroup kind="attention" runs={groups.attention} onSelect={onSelect} />}
        {groups.converged.length > 0 && <RunGroup kind="converged" runs={groups.converged} onSelect={onSelect} />}
      </main>
    </>
  );
}

function RunCard({ run, onSelect }) {
  // Renders .run-card with all sub-elements from §2.8.
}
```

Stats aggregation reads from the UNFILTERED run set (so the panel shows project-wide health regardless of the active chip), while the group sections render the FILTERED set.

---

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As a **researcher**, I want to see at a glance how much compute I've burned on stalled runs vs. converged ones, so that I can decide whether to triage failures before kicking off new runs.

> As a **researcher**, I want each run card to show me the phase where the run died and which agent contributed most of the cost, so that I can diagnose without clicking into the run.

> As a **viewer**, I want to filter runs by status and have the URL reflect my filter, so that I can share a link to "show me only the errored runs" with a teammate.

> As a **researcher**, I want a 5-bar phase strip to visually communicate how far each run made it (P1 plan → P5 sum), so that the failure pattern across many runs is legible without reading each card.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1: errored run renders the failure card**
> GIVEN the API returns a run with `id="r-13ed3f4a-91c2"`, `status="errored"`, `phases=["done","done","done","failed","pending"]`, `agents.a.cost=4.21`, `agents.b.cost=5.70`
> WHEN the researcher navigates to `/#/` and the page hydrates
> THEN the DOM contains `<article class="run-card run-card--errored">` enclosing a `<span class="rc-status rc-status--errored">` with text `errored`, a `.rc-topic` containing `Postgres multi-tenant RLS & connection-pool reset`, and `.rc-phase--failed` on the P4 cell

> **Scenario 2: filter chip click swaps the URL and re-partitions the visible groups**
> GIVEN the page has loaded with `?filter=all` (all 15 runs visible across Needs-attention + Converged sections)
> WHEN the researcher clicks the `Errored` chip (`.fchip` with text `Errored`)
> THEN the URL becomes `#/?filter=errored`, the `.fchip[aria-pressed="true"]` chip switches to `Errored`, and only `.run-card.run-card--errored` cards remain in the `.ar-grid`

> **Scenario 3: theme toggle persists to localStorage**
> GIVEN the page is rendered with `<body class="">` (dark mode, default)
> WHEN the researcher clicks the `.md-icon-btn` containing the `contrast` Material Symbol
> THEN `<body>` gains the `light` class, `localStorage.getItem('dr-theme')` returns `"light"`, and reloading the page preserves the light theme

> **Scenario 4: stats panel computes totals from the unfiltered run list**
> GIVEN the API returns 15 runs with `cost` values summing to `$95.13` and 1 run with `status=completed`
> WHEN the page renders any filter state (including `?filter=errored`)
> THEN the `.ar-stat__value` under `.ar-stat` label `Total spend` reads `$95.13`, and the `.ar-stat__value` under label `Convergence rate` reads `6.7%`

---

## 4. Data / Schema deltas

The page demands fields the current `RunListRow` does not carry. The API at [src/dual_research/ui/server.py:178-194](src/dual_research/ui/server.py#L178) (filesystem mode) and [src/dual_research/ui/server.py:742-745](src/dual_research/ui/server.py#L742) (supabase mode) returns a `list[RunListRow]`. The `RunListRow` model at [src/dual_research/ui/models.py:778-788](src/dual_research/ui/models.py#L778) (10 fields: id, display_id, status, phase, topic, started_at_ago, started_at, duration, cost, rounds) is extended **additively** — no field is renamed or removed — with:

```python
class PhaseOutcome(str, Enum):
    DONE = "done"
    ACTIVE = "active"
    FAILED = "failed"
    ABANDON = "abandon"
    PENDING = "pending"

class AgentChip(BaseModel):
    kind: Literal["", "warn", "err", "ok", "info"] = ""
    text: str

class AgentBreakdown(BaseModel):
    name: Literal["Claude", "GPT"]
    cost: float                  # 2-decimal dollars
    chips: list[AgentChip] = []  # may be empty when no derivation matches

class RunNote(BaseModel):
    variant: Literal["err", "warn", "ok"]
    icon: str                    # Material Symbol name
    html: str                    # already-formatted, uses <b>...</b>

class RunListRow(BaseModel):
    # ... existing 10 fields preserved ...
    phases: tuple[PhaseOutcome, PhaseOutcome, PhaseOutcome, PhaseOutcome, PhaseOutcome]
    rounds_completed: int        # parallel to existing `rounds` string
    rounds_max: int
    agents: dict[Literal["a", "b"], AgentBreakdown]
    note: RunNote | None
```

Derivation paths (all server-side, both filesystem and supabase modes):

- `phases`: walk the run's per-turn artifacts (existing on disk under `<run_dir>/turns/*.json`) and compute the outcome per phase by the algorithm in §2.8.5.
- `rounds_completed` / `rounds_max`: parse the existing `rounds: "n / 6"` string (or read directly from `meta.json`).
- `agents.a.cost` / `agents.b.cost`: aggregate `cost_ledger.jsonl` rows by `agent` field (existing). Round to 2 decimals.
- `agents.{a,b}.chips`: derive the three derivation-included kinds (plan turns, critiques, sources) by counting phase-tagged turns. The other chip kinds (conceded, drift, scope flip, ctx overflow, runaway loop) are emitted as **empty** until the deferred derivation specs ship — the chip list simply has fewer entries.
- `note`: derived from `status` + terminal phase + `meta.json::stopping_reason` per the template in §2.8.7.

Empty / null handling: if any derivation fails (e.g. `cost_ledger.jsonl` is missing for an old run), the field falls back to a safe default (`agents.a.cost = 0.0`, `agents.a.chips = []`, `note = None`). The card still renders — the note row simply collapses out.

The existing `/api/runs` cache at [tests/ui/test_server_cache.py:452,483](tests/ui/test_server_cache.py#L452) (spec 0079) continues to apply; cache keys stay structurally compatible since the change is additive.

---

## 5. Out of scope

This spec deliberately does **not** include:

- **Compare tab, Search tab, How-it-works tab behavior changes.** The chrome at §2.2 renders these tabs at the correct visual position with click handlers wired to the existing routes (or no-op if the target route does not yet exist). Any visual or behavioral redesign of those surfaces is deferred to follow-up specs.
- **The "New run" entry-point CTA card** sketched at `All Runs.html:597-638`. Per the handoff README §"Out-of-scope notes" (line 608), the new-run entry point lives in the existing chrome — not on this page.
- **Semantic chip-derivation kinds**: `<N> conceded`, `<N> drift`, `scope flip`. These require negotiation-thread analysis or LLM judgment. Deferred to a follow-up spec — to be drafted post-merge with disposition `defer` until prioritized. The chip vocabulary `.rc-bdg--warn` / `--err` / `--ok` / `--info` ships now in composed-components.css; the data simply isn't populated for these kinds until the follow-up lands.
- **`ctx overflow` / `runaway review loop` mechanical chip derivation**. These are mechanical (truncation-marker detection, P4 duration threshold) but their derivation is out of scope for the visual rebuild — deferred to a follow-up spec to be drafted post-merge. The chip rendering vocabulary lands; the values populate later.
- **The inline search input** and its `/`-focus keyboard shortcut at [src/dual_research/ui/static/run-list.jsx:143-155](src/dual_research/ui/static/run-list.jsx#L143). Removed. The `Search` chrome tab is the future entry point; the `?q=` query param becomes a no-op on the All Runs page (parser remains in router.jsx for backward compatibility — bookmarks with `?q=…` still resolve, the page just ignores the value).
- **Multi-select filter chips.** The current page is single-select; this spec preserves that. The handoff README suggests multi-select as a future enhancement; deferred to a follow-up spec.
- **Density toggle (`body.compact`).** Exists in the DS but not part of this rebuild — the page renders at default density.
- **Empty-state design** when a filter yields zero results. The existing empty-state pattern at first-render (loading skeleton + "no runs yet" copy) is reused as-is; visual redesign is a follow-up.
- **Run-detail page (`/#/runs/<id>`).** Unchanged. The new card's `onSelect(id)` callback routes to the existing run-detail screen.
- **`PhaseMini` shared primitive** at [src/dual_research/ui/static/run-list.jsx:489](src/dual_research/ui/static/run-list.jsx#L489). Kept intact because the run-detail timeline cards consume it. The new All Runs page uses its own `.rc-phases` 5-segment strip (§2.8.5) — they are siblings, not replacements.

---

## 6. Test plan

Tests land at [tests/test_spec_0246_all_runs.py](tests/test_spec_0246_all_runs.py) — one canonical source-pattern file per the spec 0206 doctrine at [design-system/SPEC.md §13](design-system/SPEC.md#13--ui-test-doctrine-spec-0206), using the helpers at [tests/_ui_pattern_helpers.py](tests/_ui_pattern_helpers.py).

Each pair below is a positive-presence assertion on the post-fix shape plus an antipodal-absence assertion on the pre-fix shape; this is the canonical idiom from the helpers' docstring.

- [ ] **Run card anatomy**: `tests/test_spec_0246_all_runs.py::test_run_card_renders_status_topic_metrics_id` — JSX matches `<article className=.*run-card.*run-card--errored` and `className=.*rc-status rc-status--errored` and `className=.*rc-topic` and `className=.*rc-meta__l.*Started.*rc-meta__v` and `className=.*rc-idbdg.*r-`; antipode absence — the pre-fix shape `<RunRow` from run-list.jsx:413 must not appear in `app.jsx` or `run-list.jsx` after the change.
- [ ] **5-segment phase strip**: `tests/test_spec_0246_all_runs.py::test_phase_strip_renders_five_cells_with_state_modifiers` — `.rc-phases` block contains exactly 5 `.rc-phase` children with labels `P1 plan`, `P2 nego`, `P3 res`, `P4 rev`, `P5 sum`; state modifiers `--done`, `--active`, `--failed`, `--abandon`, `--pending` are all defined in composed-components.css. Antipode absence — `<PhaseMini` is NOT consumed inside `<RunCard`.
- [ ] **Per-agent rows render Claude on sable + GPT on sage**: positive regex `\.rc-agent--a::before \{[^}]*background:\s*var\(--p-sable\)` and `\.rc-agent--b::before \{[^}]*background:\s*var\(--p-sage\)` both present in composed-components.css AND the live-app mirror at src/dual_research/ui/static/components.css. Antipode absence — agent rows must NOT inline a hex color (`#[0-9a-fA-F]{6}` absent inside `\.rc-agent.*\{[^}]*\}`).
- [ ] **Stats panel computes from unfiltered run set**: `tests/test_spec_0246_all_runs.py::test_stats_panel_aggregates_unfiltered` — JSX uses `runs` (not the filtered `visibleRuns`) as the input to `<StatsPanel stats={computeStats(runs)} />`. Antipode absence — no `<StatsPanel stats={computeStats(visibleRuns)}` regex match anywhere in run-list.jsx.
- [ ] **Filter chip row matches the seven canonical statuses in order**: positive regex matches an ordered sequence `All`, `Running`, `Converged`, `Deadlocked`, `Errored`, `Abandoned`, `Completed` inside the `<FilterChipRow>` JSX. Antipode absence — the deleted `<input type="search"` from run-list.jsx:143 is gone.
- [ ] **No inline `style={{` props remain on the new tree**: positive regex `<article className="run-card` followed within 200 chars by no `style={{`. Antipode absence — the old `RunRow` component is fully deleted from run-list.jsx (no `function RunRow(`).
- [ ] **Both component files in sync**: composed-components.css and src/dual_research/ui/static/components.css both define every new class (`.run-card`, `.run-card--errored`, `.run-card--abandoned`, `.run-card--completed`, `.run-card--running`, `.rc-status`, `.rc-status--errored`, `.rc-topic`, `.rc-idbdg`, `.rc-phases`, `.rc-phase`, `.rc-phase--done`, `.rc-phase--active`, `.rc-phase--failed`, `.rc-phase--abandon`, `.rc-phase--pending`, `.rc-agent`, `.rc-agent--a`, `.rc-agent--b`, `.rc-agent__cost`, `.rc-agent__name`, `.rc-bdg`, `.rc-bdg--warn`, `.rc-bdg--err`, `.rc-bdg--ok`, `.rc-bdg--info`, `.rc-note`, `.rc-note--err`, `.rc-note--warn`, `.rc-note--ok`, `.ar-chrome`, `.ar-tab`, `.ar-pill`, `.ar-project`, `.ar-stats`, `.ar-stat`, `.ar-stat--phase`, `.phase-dist`, `.ar-filters`, `.fchip`, `.ar-sort`, `.ar-group`, `.ar-group--warn`, `.ar-grid`).
- [ ] **API `RunListRow` carries the new fields**: integration test on `/api/runs` asserts the response shape includes `phases`, `agents.a.cost`, `agents.b.cost`, `agents.{a,b}.chips`, `note` keys. Extends the existing test surface at [tests/ui/test_server_cache.py:452](tests/ui/test_server_cache.py#L452).

PR-description proof: per [design-system/SPEC.md §13.2](design-system/SPEC.md#132--canonical-static-pattern-shape), embed Claude Preview MCP screenshot captures of (1) dark theme full page, (2) light theme full page, (3) hover state on a `.run-card`, (4) `?filter=errored` state showing only one section, (5) responsive breakpoint at 760 px. These are visual proofs; the source-pattern tests above are the regression guards.

---

## 7. Risks

- **Risk:** The `phases` array derivation server-side reads per-turn artifacts on every `/api/runs` hit; for a workspace with many runs this could slow the endpoint. **Mitigation:** the existing `/api/runs` cache (spec 0079, [tests/ui/test_server_cache.py:452](tests/ui/test_server_cache.py#L452)) covers this — derivation lands inside the cached path. If profiling shows a regression, precompute `phases` into `meta.json` on run finalization and read from there.
- **Risk:** The new `.ar-*` / `.rc-*` namespaces leak into the run-detail page if a developer copies a class name out of context. **Mitigation:** scope all new classes under the `.ar-page` container in composed-components.css comments so it's clear they belong to the All Runs page; the run-detail page does not include `.ar-page` in its tree.
- **Risk:** The chip rendering vocabulary lands but the semantic-chip derivation specs (§5) are never prioritized, leaving some agents with empty `chips` arrays indefinitely. **Mitigation:** acceptable — the cards still render correctly with whichever chips are derivable. Empty chip lists collapse out cleanly. The visual rebuild is the point; chip enrichment is purely additive thereafter.
- **Risk:** Removing the inline search bar breaks a user's keyboard workflow (`/` shortcut). **Mitigation:** documented in §5; the Search tab in the chrome is the future entry point. The user explicitly asked to remove every current-page element; the loss is by design.
- **Risk:** Both `composed-components.css` and `src/dual_research/ui/static/components.css` must stay in sync per the project rule — a developer could update only one. **Mitigation:** the test at the bottom of §6 ("Both component files in sync") asserts class-name parity by string-matching every new class in both files. CI catches drift.
- **Risk:** The handoff bundle is not checked into the repo — future-me cannot see the source of truth visually. **Mitigation:** §1.1 transcribes every load-bearing measurement, token, and state into this spec. The spec is self-contained.
