---
kind: dev
spec: "0177"
slug: dashboard-redesign-v3-horizontal-hero-and-metrics
title: Dashboard redesign v3 — horizontal hero + timeline, full-width counter row, populated Metrics tab, pagination, pastel chart palette, light default
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
queue_position: 1
depends_on: []
complexity: L
created: 2026-05-22
queued_at: "2026-05-22T20:48:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

# Spec 0177 — Dashboard redesign v3 — horizontal hero + timeline, full-width counter row, populated Metrics tab, pagination, pastel chart palette, light default

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** —
> **Bump:** MINOR — new visualisations, new pagination primitive, new chart token family. No removed APIs.
> **Evidence:** mockup at [`dashboard/mockups/dashboard-redesign-v3-horizontal.html`](../dashboard/mockups/dashboard-redesign-v3-horizontal.html) — the visual contract for this spec. Live dashboard: [https://lexiz.github.io/dual-research/](https://lexiz.github.io/dual-research/).

---

## 1. Context

Spec [0169](0169-dashboard-redesign-v2-tabs-themes-history.md) introduced the callout strip (`.strip`) with a 3-column grid: hero (~60%) + counter cluster (~25%) + avg-cycle card (~15%), see [`scripts/spec_lifecycle/render_dashboard.py:1734`](../scripts/spec_lifecycle/render_dashboard.py#L1734). When the hero is in flight it switches to `.hero--inflight` and stacks a vertical stage timeline beneath itself — but the right two grid columns (counters + avg-cycle) stay at their original height, leaving a tall vertical gap on the right side of the strip. The horizontal real estate is under-used and the timeline column is awkwardly narrow.

The Metrics tab is also a regression vs. user expectation. It currently renders only [`_render_metrics`](../scripts/spec_lifecycle/render_dashboard.py#L604) — four tiles (Avg cycle / Throughput / Reconcile patches / Failed cycles). The History tab's [All specs table](../scripts/spec_lifecycle/render_dashboard.py#L803) shows status + target_version but no per-spec timing — neither how long the spec sat in the queue (lifetime) nor how long the dev cycle itself took. The user has asked for both, plus actual charts on Metrics.

## 2. Proposed change

The mockup file [`dashboard/mockups/dashboard-redesign-v3-horizontal.html`](../dashboard/mockups/dashboard-redesign-v3-horizontal.html) is the visual contract. Reproduce it inside the renderer.

### 2.1 — Layout: horizontal hero + 5-column counter row

Replace the current `.strip` 3-column grid at [`render_dashboard.py:1734`](../scripts/spec_lifecycle/render_dashboard.py#L1734) with two stacked full-width regions:

1. **Hero row** — `data-region="hero"`, full container width, single card.
2. **Counter row** — `data-region="counters"`, full container width, 5 cards in a row.

The Avg-cycle card folds into the counter row as the 5th counter (one of: Drafts · Queued · In flight · Shipped · **Avg cycle (last 10)**). Drop the separate `data-region="avg"` container; merge [`_render_avg_cycle_card`](../scripts/spec_lifecycle/render_dashboard.py#L937) into [`_render_counter_cluster`](../scripts/spec_lifecycle/render_dashboard.py#L903) (which becomes a 5-counter renderer). Update the bootstrap client's `renderHero` / `paint` calls in [`render_dashboard.py:2408`](../scripts/spec_lifecycle/render_dashboard.py#L2408) so the avg-cycle region is no longer swapped independently.

The avg-cycle counter carries the rolling-10 delta sub-line (`↓ 1m 24s vs prior 10`) and an inline SVG sparkline (12 data points minimum, last 12 deployed cycles). The other four counters retain their current shape.

CSS: replace the `.strip { grid-template-columns: 1.6fr 1fr 0.6fr; }` block with `.strip { display: contents; }` (or remove the wrapper entirely) and let the hero + counter sections sit as direct children of `.page`. Move the responsive collapse rules at [`render_dashboard.py:1813`](../scripts/spec_lifecycle/render_dashboard.py#L1813) to match.

DS citation: `.counter` cards use the **Card** primitive per [design-system/SPEC.md §3](../design-system/SPEC.md#L314) (`--md-shape-md`, surface-container). Section heading bar (`.sh`) is the page-level pattern used throughout the dashboard.

### 2.2 — Horizontal in-flight timeline

The current [`_render_hero_inflight`](../scripts/spec_lifecycle/render_dashboard.py#L435) emits an `<ol class="stages">` with [`_render_stage_row`](../scripts/spec_lifecycle/render_dashboard.py#L407) items in a CSS grid `24px 150px 1fr 80px` (vertical list). Replace with a horizontal track:

- Add `_render_stage_node(stage)` — emits `<div class="tl__step tl__step--{status}">` with `.tl__node` (28×28 circle), `.tl__lbl` (stage name), `.tl__dur` (duration).
- Replace the `<ol class="stages">` block at [`render_dashboard.py:530`](../scripts/spec_lifecycle/render_dashboard.py#L530) with a `<div class="tl">` containing:
  - `<div class="tl__rail">` — background rail across the row.
  - `<div class="tl__rail-done">` — overlay rail in the ok colour, width = `(done_count / total) * 100%`.
  - `<div class="tl__steps">` — `grid-template-columns: repeat(N, 1fr)` where N = total stages.
- Stage list is unchanged — still computed by [`compute_stages`](../scripts/spec_lifecycle/stages.py) and labelled via `STEP_LABELS`. `data-stage-started-at` attribute moves from the duration `<span>` onto the current node's `.tl__dur` cell so the live-ticker in [`DASHBOARD_LIVE_JS`](../scripts/spec_lifecycle/render_dashboard.py#L1953) keeps working.

Node states:
- `tl__step--done` — pastel-green fill + `✓`.
- `tl__step--curr` — info-blue fill, pulsing halo (reuses `@keyframes halo` from [`render_dashboard.py:1407`](../scripts/spec_lifecycle/render_dashboard.py#L1407)), centre dot.
- `tl__step--queued` — surface-container fill, no glyph.
- `tl__step--fail` — err fill + `!`.

Responsive: at `max-width: 700px` the `.tl__steps` row falls back to `overflow-x: auto` so the row can scroll horizontally on phones rather than crushing labels.

### 2.3 — History tab: Lifetime + Cycle columns

[`_render_all_specs`](../scripts/spec_lifecycle/render_dashboard.py#L803) currently emits a 5-column grid (`76px 1fr 130px 100px 100px` — Spec · Title · Type · Status · Version). Add two columns to the right:

- **Lifetime** — wall-clock from `created` (fallback `queued_at`) to `deployed_at`, formatted with `_humanize_seconds` extended to days/weeks for long values. Uses YAML-frontmatter dates → `dt.datetime`.
- **Cycle** — agent-time from `started_at` to `deployed_at`. `SpecRow.cycle_seconds` at [`render_dashboard.py:79`](../scripts/spec_lifecycle/render_dashboard.py#L79) already computes this — just surface it.

New grid: `70px 1fr 110px 100px 90px 90px` (Spec · Title · Type · Status · Lifetime · Cycle). Drop the `Version` column — `target_version` is rarely meaningful for shipped specs and reclaims width for the timing columns. (If retained version is requested in review, swap the smallest column out.)

When either lifetime or cycle is unavailable (queued / in-flight / failed specs), render `—`.

The bootstrap client's `renderAllSpecs` at [`render_dashboard.py:2377`](../scripts/spec_lifecycle/render_dashboard.py#L2377) must mirror the same column changes so the live-data refresh paints the same shape.

### 2.4 — Metrics tab: full populate

Replace the body of [`_render_metrics`](../scripts/spec_lifecycle/render_dashboard.py#L604) with a multi-section layout. All charts are inline SVG — no external chart libraries.

**2.4.1 — Top callout strip** (3 tiles, horizontal):
- *Cycle time WoW* — `(mean_last_7d - mean_prior_7d) / mean_prior_7d`. Tone: `--ok` if delta ≤ 0, `--warn` if > 0. Title: "Cycle time improving" / "Cycle time slowing".
- *Where time goes* — name of the largest stage in the mean stage-breakdown, with its share %. E.g. "62% in implement".
- *Reconcile drift* — `needed_fix / reconciled` over last 10 deployed cycles (same source as [`render_dashboard.py:639`](../scripts/spec_lifecycle/render_dashboard.py#L639)).

**2.4.2 — Cycle time line chart** — last `N=22` deployed cycles, `viewBox="0 0 600 220"`. Two polylines: actual cycle time (`var(--chart-blue)`) and rolling-10 mean overlay (`var(--chart-purple)`, dashed). Dot markers on the actual line. Y-axis: 0 / 5m / 10m / 15m / 20m. X-axis labels: every 5th spec id. Clip cycles > 1h (e.g. 0152) so the chart isn't dominated by one outlier — annotate the clip in the caption.

**2.4.3 — Stage breakdown stacked bar** — mean stage durations across the last 10 deployed cycles. Data source: per-spec events from `dashboard/events/NNNN.jsonl` (read via [`read_events`](../scripts/spec_lifecycle/append_event.py)). For each step pair (preflight_ok→reconcile_complete, reconcile_complete→branched, branched→implement_complete, etc.) compute mean seconds. Render as a single horizontal stacked bar. Legend below.

**2.4.4 — Throughput per week bars** — last 8 weeks, count of `deployed` specs per ISO week. Current week shaded with `var(--chart-purple)`, prior weeks with `var(--chart-blue)` at graduated opacity (0.55 → 0.90).

**2.4.5 — By-type horizontal bars** — last 30 days, deployed-spec count grouped by `type` (new-feature / bug / refactoring / test / breaking). Bar fill width = `count / max_count`; right-aligned label = `<count> · <mean_cycle>`. Colours: blue / pink / yellow / mint / peach respectively.

**2.4.6 — Success rate donut** — last 30 days, `deployed / (deployed + failed)`. SVG donut with `stroke-dasharray` arc; centre text = percentage; legend below.

**2.4.7 — Authoring funnel** — drafts → queued → in-flight → deployed (last 30 days). Four horizontal rectangles, decreasing height (suggestion of funnel). Drafts pulled from current draft count + drafts promoted in last 30 days. Other counts from spec frontmatter timestamps.

All metrics computations live inside `_render_metrics`. Add a `_compute_stage_durations(events: list[dict]) -> dict[str, int]` helper if it grows long enough to warrant.

### 2.5 — Pastel chart palette

Introduce nine pastel chart tokens, scoped to the Metrics tab. Place token definitions in [`design-system/assets/styles/tokens-and-primitives.css`](../design-system/assets/styles/tokens-and-primitives.css) (light + dark variants) so they are available to any future surface that wants them, but the `_render_metrics` output is the only consumer for this spec:

```
--chart-blue, --chart-purple, --chart-green, --chart-yellow,
--chart-pink, --chart-peach, --chart-mint, --chart-grey, --chart-track
```

Light-mode values from the mockup (`#a8c8e8 / #c8b5e8 / #b8dcc0 / #f0deaa / #f0bcc0 / #f4ccb0 / #b8dcd4 / #d8dde3 / #ecf0f4`); dark-mode adjusted (`#7fa8d8 / #b89edc / #94c8a4 / #e0c890 / #e0a4ac / #e0b498 / #94c4bc / #6a7480 / #232b35`). Final values to be confirmed against existing `--p-*` tokens during implementation — prefer existing tokens where the hue matches.

The status chips (`tone-info`, `tone-ok`, `tone-warn`, `tone-err`) and live-state colours (hero halo, in-flight chip, queue rows) keep their current bold tones. **Do not replace `--p-info` / `--p-ok` etc. with pastels.** Pastels apply only inside `.tab-panel[data-panel="metrics"]` charts.

DS citation: this extends the **2.1 Palette** section of [design-system/SPEC.md](../design-system/SPEC.md#L44) with a new chart-palette sub-family. Update SPEC.md in this same spec to document the new tokens — see § 5 (Out of scope) for what the SPEC.md update does NOT include.

### 2.6 — Pagination on Queue + Recent activity

Both [`_render_queue`](../scripts/spec_lifecycle/render_dashboard.py#L685) and [`_render_feed`](../scripts/spec_lifecycle/render_dashboard.py#L723) currently emit all rows (queue has no cap, feed caps at 40 in code at [`render_dashboard.py:751`](../scripts/spec_lifecycle/render_dashboard.py#L751)). Add client-side pagination — cap visible rows at 10 per page.

- Server emits all rows (or feed: up to 40) inside the section, with the `data-pager-page` attribute on each row indicating which page it belongs to (`1`, `2`, …). Rows on pages > 1 carry `hidden` initially.
- A new `_render_pager(total_rows: int, label: str) -> str` helper emits the `.pager` strip: `"Showing X–Y of N"` + `← page-number-buttons →`. Disabled prev on page 1, disabled next on last page. Mid-pages collapsed into an ellipsis when total > 5 pages.
- New JS in [`DASHBOARD_LIVE_JS`](../scripts/spec_lifecycle/render_dashboard.py#L1953) wires button clicks to toggle `[hidden]` on `[data-pager-page]` rows. Each `.pager` is scoped to its parent section via the section's `aria-label`.
- The bootstrap client's `renderQueue` / `renderFeed` at [`render_dashboard.py:2273`](../scripts/spec_lifecycle/render_dashboard.py#L2273) / [`render_dashboard.py:2306`](../scripts/spec_lifecycle/render_dashboard.py#L2306) must emit the same pager strip and `data-pager-page` attributes so live re-renders don't strip the pagination.

DS citation: new `.pager` component — add to both [`design-system/assets/styles/composed-components.css`](../design-system/assets/styles/composed-components.css) and [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) in one commit, per CLAUDE.md "New components land in two places in one commit" rule. Tokens only — no hex codes.

### 2.7 — Default theme: light

[`_render_theme_init_script`](../scripts/spec_lifecycle/render_dashboard.py#L1065) currently defaults to `'auto'` when no `localStorage` value is present. Change the default to `'light'`. The toggle in [`DASHBOARD_LIVE_JS`](../scripts/spec_lifecycle/render_dashboard.py#L2058) still cycles `light → dark → auto` — only the unset default changes.

Returning users with a stored preference keep it. New visitors get light.

## 3. UX / Behavior

Before: the dashboard's hero strip leaves a vertical empty band when in flight, the History tab's All-specs table shows no timing data, and the Metrics tab is functionally empty. Default theme is auto (system-driven), which can flash dark on light-mode systems.

After: hero spans full width with a horizontal stage timeline; counter row sits beneath as 5 equal cards including avg-cycle; History rows carry Lifetime + Cycle columns; Metrics tab shows 3 callouts, a cycle-time trend, stage breakdown, weekly throughput, by-type breakdown, success-rate donut, and authoring funnel; default theme is light.

State coverage (mockup-confirmed):
- **Idle hero** — full-width banner, no timeline visible. Existing layout, just stretched horizontally.
- **In-flight hero** — full-width banner + horizontal timeline beneath. Current node pulses; rail fills as stages complete.
- **Counter row** — 5 cards equally distributed. Counts source from same data as today.
- **Tabs unchanged** — Now / Spec creation / History / Metrics. Counts on tab badges unchanged.

Pagination:
- Queue table: 10 rows per page, pager strip below. Default page 1.
- Recent activity: 10 rows per page, pager below. Currently capped at 40 server-side — keep that cap; pages 1–4.
- Page state is not persisted across reloads (no router, no hash).

## 4. Data / Schema deltas

None. All metrics derive from existing data sources:

- Spec frontmatter (`specs/*.md`)
- Per-spec events (`dashboard/events/NNNN.jsonl`)
- Live `/api/data` payload — schema unchanged.

No new files. No new migrations. No new API endpoints.

## 5. Out of scope

- **No `target_version` column rescue.** The History table swaps the Version column for Lifetime + Cycle. If reviewers want Version back, that's a follow-up — not in this spec.
- **No fancy chart-library dependency.** Charts are inline SVG, hand-rolled. Adopting Chart.js or D3 is a separate decision.
- **No tooltips on chart elements.** Charts render with labels embedded; hover-tooltips are a future polish.
- **No persisted pagination state.** Page resets to 1 on every reload — no `localStorage`, no URL hash.
- **No SPEC.md re-architecture.** § 2.5 adds chart tokens to [design-system/SPEC.md §2.1](../design-system/SPEC.md#L44) under a new "Chart palette" sub-heading; it does NOT restructure the existing palette docs.
- **No Cloudflare Pages function changes.** [`functions/api/data.ts`](../functions/api/data.ts) (or wherever the Function lives) is untouched — payload shape is unchanged.
- **No event-schema changes.** `dashboard/events/NNNN.jsonl` formats stay as-is; the stage-breakdown chart computes durations from existing event sequences.
- **No dark-mode mockup parity audit.** The mockup is light-default and includes dark colours; minor dark-mode pastel touch-ups are acceptable in implementation without requiring a new mockup pass.

## 6. Test plan

- [ ] `uv run scripts/spec_lifecycle/render_dashboard.py --repo-root . --out /tmp/dash` exits 0 and emits an `index.html` whose hero region matches the mockup's structure (full-width, no flanking grid).
- [ ] In-flight render — point the renderer at a spec with `status: in_progress` (e.g. mock fixture spec) and assert the output contains `<div class="tl">` with `tl__steps` and ≥ 10 `tl__step` children.
- [ ] History tab — assert the All-specs grid declares 6 columns (`70px 1fr 110px 100px 90px 90px`), with column headers "Spec / Title / Type / Status / Lifetime / Cycle" and at least one row showing both lifetime and cycle as non-`—` (a deployed spec).
- [ ] Metrics tab — assert the output contains `<svg class="chart"` for at least four distinct charts (line, stacked bar, throughput bars, donut) and that the callout strip carries 3 `.callout` cards.
- [ ] Pastel tokens — assert `tokens.css` (copied from design-system) contains `--chart-blue` and `--chart-purple` definitions in both light and dark blocks.
- [ ] Pagination — assert `_render_queue` output contains a `.pager` strip when `len(queued) > 10`, AND the rows from index 10 onward carry `hidden` attribute and `data-pager-page="2"`.
- [ ] Light default — render `_render_theme_init_script` and assert the inline script body contains `||'light'` (or equivalent default fallback), not `||'auto'`.
- [ ] DS sync — assert the new `.pager` block exists in BOTH [`design-system/assets/styles/composed-components.css`](../design-system/assets/styles/composed-components.css) AND [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) (grep for `.pager {`).
- [ ] Existing tests — `uv run pytest tests/ -q` stays green (no regressions in renderer tests, lifecycle tests, dashboard event tests).
- [ ] Visual smoke — open the locally-rendered `dashboard/site/index.html` and confirm it matches the mockup in light mode (counter row · hero · in-flight horizontal timeline · populated Metrics tab · pagination strips visible on Queue + Recent activity when row count > 10).

## 7. Risks

- **Stage-breakdown chart needs event data that may be missing on older specs.** Pre-0152 specs lack per-step branch events. *Mitigation*: filter the mean-durations calculation to specs that have a `cycle_started` event and at least one `implement_complete` event. If the filtered set is < 3, render the chart with a "Insufficient data — needs more cycles with full timings" callout instead.
- **The bootstrap client (`DASHBOARD_BOOTSTRAP_JS`) duplicates a lot of renderer logic.** Every renderer change must be mirrored in the JS or the live refresh will revert to the old shape. *Mitigation*: implement renderer changes and JS changes in the same commit. Add an assertion in the test plan that diff'ing the rendered HTML against the JS-painted HTML for a fixture produces the same structure.
- **Removing the `target_version` column may surprise reviewers.** *Mitigation*: call this out explicitly in § 5 and the PR description; revertible by swapping one column back.
- **Pastel palette may have insufficient contrast in dark mode.** *Mitigation*: tune dark-mode values to ≥ 4.5:1 against `--md-surface-container` per WCAG AA — explicit check in implementation, not just a vibe call.
- **In-flight horizontal timeline can crush labels at narrow widths.** *Mitigation*: the responsive rule at `max-width: 700px` falls back to `overflow-x: auto` so the row scrolls rather than overflowing.
- **Pagination state resets on /api/data refresh.** Every 5s the bootstrap client repaints — if a user is on page 2 of the activity feed, the refresh drops them back to page 1. *Mitigation*: capture `currentPage` in a closure inside the JS pager wiring and reapply it on re-render. If that adds too much complexity, accept the reset and call it out in the PR — the activity feed is most-recent-first so page 1 is the relevant page anyway.
