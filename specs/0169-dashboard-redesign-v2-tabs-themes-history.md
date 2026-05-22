---
kind: dev
spec: "0169"
slug: dashboard-redesign-v2-tabs-themes-history
title: Dashboard redesign v2 — condensed callouts, tabs, light/dark themes, History total-elapsed banner
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.30.0
status: merged
queue_position: 1
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T17:37:52Z"
started_at: "2026-05-22T21:10:00Z"
merged_at: "2026-05-22T21:55:00Z"
deployed_at: ""
pr: "https://github.com/Lexiz/dual-research/pull/192"
handover: ""
failure_step: ""
source_session: dashboard-mockup-2026-05-22
promoted_from_draft: ""
---

# Spec 0169 — Dashboard redesign v2 — condensed callouts, tabs, light/dark themes, History total-elapsed banner

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — new UI surfaces (tabs, history banner, metrics, theme toggle).
> **Evidence:** mockup at `dashboard/mockups/0169-dashboard-redesign-v2.html` (committed alongside this spec). Builds on [spec 0153](specs/0153-dashboard-redesign-staged-hero-and-activity-feed.md), [spec 0156](specs/0156-dashboard-liveness-improvements.md), [spec 0160](specs/0160-dashboard-live-data-via-pages-function.md), [spec 0163](specs/0163-push-events-to-main-during-branch-phase.md).

---

## 1. Context

The current dashboard (rendered by `scripts/spec_lifecycle/render_dashboard.py:874`) stacks three full-width callout blocks above the queue — hero, pipeline strip, metrics row — each ~90px tall and each summarising queue health in slightly different language. They compete for the eye, push the queue and activity feed below the fold on a 1366×768 laptop screen, and the metrics row's "Reconcile patches" / "Failed cycles" tiles are rarely consulted at-a-glance. Recent activity caps at 24h/40 rows and all-specs is dumped as one ungrouped list (already 65+ deployed-status rows and growing), with no way to filter, search, or page. There is no light/dark toggle even though the design system at `design-system/SPEC.md` §6 already defines tokens for both themes (the live app has a working toggle).

Beyond layout, the dashboard does not surface cumulative time-spent across deployed runs — only per-cycle. The user asked specifically for a prominent "total elapsed across all previous runs" view as evidence of how much agent-hours the system has accumulated, plus a side-by-side mean/median/fastest/slowest comparison. The current `_render_metrics()` at `scripts/spec_lifecycle/render_dashboard.py:598` exposes rolling-10 avg and 24h throughput but no totals and no distribution.

## 2. Proposed change

Rewrite the rendered shape produced by `render_index()` and `DASHBOARD_BOOTSTRAP_JS` in `scripts/spec_lifecycle/render_dashboard.py` (server-side render_dashboard.py:874 and client-side bootstrap at render_dashboard.py:1534 must stay in lock-step — they target the same `data-region` containers). The data shape served by `functions/api/data.js` does **not** change; only the rendering does. The complete reference is `dashboard/mockups/0169-dashboard-redesign-v2.html` — implementers should open it in a browser to see exact layout, motion, and color decisions in both themes.

### 2.1 — Condensed callout strip (replaces hero + pipeline + metrics stack)

A single row, three cards, ~96px tall total:

- **Hero card** (~60%): unchanged content (idle or in-flight), styling tightened to `--md-shape-corner-large` (DS §2.6) on top-level radius. Idle shows last-deploy spec id + slug + "Xh Ym ago"; in-flight shows step kicker + spec link + chips + elapsed.
- **Counter cluster card** (~25%): four counters in a single row — `Drafts / Queued / In flight / Shipped` — each as `<label>` + `<number>` + 1-word sublabel ("ideation" / "pending" / "running" / "all-time"). The sublabel cell carries `white-space: nowrap; overflow: hidden; text-overflow: ellipsis` to prevent line-wrap at narrow widths. Replaces the current 5-column `.pipe` strip at render_dashboard.py:556 (the "Merged today" column folds into the activity feed instead).
- **Avg cycle card** (~15%): big mono number (rolling-10 mean), with a `↓ Xm vs prior 10` delta line. Same data the current `_render_metrics()` computes; just isolated into the strip as the at-a-glance KPI.

Other metrics (throughput, failed-cycle count, reconcile rate, deferrals, queue-dwell) move to the Metrics tab in §2.5. Cite DS §3 for chip primitives, §2.2 for surface elevation, §2.9 for card elevation.

### 2.2 — Tabbed body (replaces flat scroll)

A `nav.tabs` immediately below the callout strip with four tab buttons: **Now · Spec creation · History · Metrics**. The active tab carries an underline in `--p-info` (DS §3). Tab content is rendered as four `<section class="tab-panel">` siblings; only one has `aria-hidden="false"` at a time. Switching is CSS-only (display:none/block) — no route hash, no state persistence between visits.

Tab counts (e.g. "Now 5", "Spec creation 6") are derived counts shown in a small pill next to each label. Use the same per-tab counters that drive the callout cluster.

### 2.3 — `Now` tab content (always-unfolded dev progression)

When `in_flight` is non-empty: render `_render_hero_inflight()` (already exists at render_dashboard.py:429) as a full stage-timeline card **expanded by default** at the top of the Now tab — directly under the section heading, no accordion, no toggle. The 11-stage timeline (Pre-flight → Read handoff → Read spec → Reconcile → Branch → Implement → Test → PR → Merge → Deploy → Handoff) shows done / current / queued state per stage with per-stage durations and notes — the existing `compute_stages()` from `scripts/spec_lifecycle/stages.py:88` already produces this data. **This expanded progression is dev-cycle-only** — the Spec creation tab in §2.4 does NOT get an equivalent unfolded stage timeline.

Below the in-flight card, render the queue table (current `_render_queue()` at render_dashboard.py:679) plus a dev-side `_render_feed()` at render_dashboard.py:717 filtered to step names that appear in the dev cycle. When `in_flight` is empty, omit the timeline card — the queue + feed become the tab content.

### 2.4 — `Spec creation` tab content

Renders the drafts table (current `_render_drafts()` at render_dashboard.py:765) plus a spec-side activity feed filtered to `queued` events only (i.e. emissions from `/spec-queue` and `/spec-promote`). No stage-timeline card here — spec creation events do not exist yet (separate future work, see §5).

### 2.5 — `History` tab content (total-elapsed banner + paginated all-specs)

Leads with a **Total time spent** banner — a single full-width card with four tiles in one row:

- **Total elapsed** — sum of `cycle_seconds` across all deployed specs that have both `started_at` and `deployed_at` set. Big mono number in `Xh Ym` (or `Xd Yh` if > 24h). Subtext: "across N timed cycles".
- **Mean cycle** — arithmetic mean excluding the bootstrap outlier (any cycle > 1h is excluded — there are currently 0 such specs apart from 0152 at 10.8h, which is the lifecycle bootstrap and should be flagged). Subtext: "excluding outliers > 1h".
- **Median cycle** — p50 of all timed runs (including outliers). Subtext: "p50 of timed runs".
- **Fastest / Slowest** — two mono numbers separated by `/`, with `<small>` for the slash. Subtext: spec ids of each.

Below the banner: the existing `_render_all_specs()` table at render_dashboard.py:797 gets new columns and behavior:

- **Cycle column** — moved from absent to a sortable last column. Renders as `<fmt>{cycle} <bar>` where `<bar>` is a 56px-wide horizontal indicator color-coded by speed bucket: `< 6m` → `--p-ok`, `6–15m` → `--p-info` (default), `15–30m` → `--p-warn`, `> 30m` → `--p-err`. Bar width = `cycle / max_cycle * 100%`.
- **Filter chip row** above the table — buttons for `All / Deployed / Queued / Failed / bug / new-feature / refactoring`. Toggleable via `aria-pressed`.
- **Search input** — substring match on title + spec number.
- **Pagination** — 10 rows per page, prev/next/numeric buttons at the bottom (CSS-only initial render; click handlers wired via vanilla JS in `DASHBOARD_BOOTSTRAP_JS`).

All this stays client-side: the JS slices, filters, sorts the same `data.specs` array the bootstrap already fetches at render_dashboard.py:1879.

### 2.6 — `Metrics` tab content

Two-column grid:

- **Cycle time over deploys** (left, ~1.4fr) — a bar chart of the last 12 timed cycles in ascending spec order. Each bar's height = `cycle / max * 100%` and color follows the same fast/normal/slow/very-slow buckets as the History column. Hover (or focus) reveals a tooltip with `<spec> · <fmt cycle>`. The chart is plain HTML+CSS — no chart library, no SVG (`<div>` per bar with `height: N%` and `::before` for label). Cite the mockup `<div class="chart">` for the exact markup.
- **By type / Reconcile** (right, ~1fr) — two stacked horizontal-bar lists. First lists each `type` (new-feature / bug / refactoring / test) with count and bar of `count / total * 100%`. Second lists reconcile outcomes (clean / mechanical) computed from the `reconcile_complete` events for the last 10 deployed cycles.

Below: a four-tile row (Throughput / Failed cycles / Deferrals / Queue dwell). These replace the metrics row that the current dashboard renders inline at render_dashboard.py:598; the new versions live exclusively under the Metrics tab.

### 2.7 — Theme toggle (light + dark)

The DS at `design-system/SPEC.md` §6 already defines both palettes. The dashboard currently follows whatever the host system serves (the tokens-and-primitives.css contains both sets keyed by `prefers-color-scheme`). Add a manual toggle:

- **Button** in the header next to the version chip. Cycles through `light → dark → auto` (auto = follow system preference). Uses Material Symbols `light_mode` / `dark_mode` / `brightness_auto` icon (current dashboard already loads Material Symbols at render_dashboard.py:48).
- **Mechanism** — sets `data-theme` on `<html>`. The dashboard's `dashboard.css` (currently inlined as `DASHBOARD_CSS` at render_dashboard.py:1078) gains theme guards: `[data-theme="light"]`, `[data-theme="dark"]`, and `[data-theme="auto"] @media (prefers-color-scheme: ...)` blocks that select the appropriate token set from `tokens.css`. Since the design system's `tokens-and-primitives.css` keys its dark tokens by `prefers-color-scheme: dark`, we need a small shim block in `DASHBOARD_CSS` that re-projects the dark token values onto `[data-theme="dark"]` and the light values onto `[data-theme="light"]`. The shim is dashboard-local — does NOT modify `design-system/assets/styles/tokens-and-primitives.css`.
- **Persistence** — toggle state stored in `localStorage` under key `dr-dashboard-theme`. Read on bootstrap (`DASHBOARD_BOOTSTRAP_JS` at render_dashboard.py:1534) before first paint to avoid a theme flash.
- Honors `prefers-reduced-motion` per DS §2.11: the toggle's pulse/transition animations disable when the user has reduced motion enabled.

### 2.8 — Files touched

- `scripts/spec_lifecycle/render_dashboard.py` — rewrite of `render_index()`, replacement of `_render_pipeline()` + `_render_metrics()` callsites with the new callout strip; new `_render_callout_strip()`, `_render_tabs()`, `_render_history_tab()`, `_render_metrics_tab()`, `_render_total_elapsed_banner()`, `_render_cycle_chart()` helpers; matching updates to `DASHBOARD_BOOTSTRAP_JS` to render the same shape client-side; `DASHBOARD_CSS` rewrite for the new structure; theme shim block.
- `dashboard/mockups/0169-dashboard-redesign-v2.html` — already committed alongside this spec as the visual reference.
- `tests/test_render_dashboard.py` (or equivalent — verify the actual path during implementation) — new tests per §6.
- `CHANGELOG.md` — new MINOR release entry.

### 2.9 — Design-system citations

- §2.1 Palette + §6 Themes — light/dark token sets used as-is. No new color tokens.
- §2.2 Surfaces — card backgrounds via `--md-surface-1` / `--md-surface-2` tonal scale.
- §2.5 Typography — `Roboto Flex` (sans, already loaded) for chrome; `Roboto Mono` or fall back to system mono for cycle numbers (the mockup uses `ui-monospace` — confirm fallback policy at implement time).
- §2.6 Shape — `--md-shape-corner-large` (14px) on the top-level cards, `--md-shape-corner-medium` (10px) on the tables.
- §2.7 Spacing — 8dp grid; the strip's internal padding is 16/24.
- §2.11 Motion — pulse animation on the in-flight hero icon is the same one defined at render_dashboard.py:1149 (`@keyframes halo`). No new motion.
- §2.13 Focus ring — tab buttons and the theme toggle button receive the DS focus ring.
- §3 Primitives — `.chip` (DS §3) is the chip primitive; the dashboard reuses it. `chip-type` modifier already exists for type labels.
- §8 Accessibility — `aria-selected` on tabs, `aria-hidden` on inactive panels, `aria-pressed` on filter chips, focus-visible respected.
- §9 Badge governance — type chips use the existing tone mapping (new-feature → info, bug → err, refactoring → warn, test → neutral) defined at render_dashboard.py:209. No new badge kinds.

The mockup at `dashboard/mockups/0169-dashboard-redesign-v2.html` uses ad-hoc palette tokens (`--bg-page`, `--text-1`, etc.) for portability outside the repo — the implementation MUST bind to `--md-*` and `--p-*` tokens, not invent new ones.

## 3. UX / Behavior

**Before (current dashboard at https://lexiz.github.io/dual-research/):**

1. Header
2. Hero (140px)
3. Pipeline strip (90px)
4. Metrics row (90px)
5. Queue table
6. Recent activity (24h, top 40)
7. Drafts
8. All specs (full ungrouped list)

Scroll-required to see the queue on a 1366×768 laptop after step 3.

**After:**

1. Header (with theme toggle + manual icon)
2. Callout strip (one row, 96px total) — hero + counters + avg
3. Tab bar
4. Active tab content

Active by default: **Now** tab → in-flight unfolded card (if any) + queue + dev feed. Queue and current-in-flight are fully visible above the fold on a 1366×768 laptop.

The `History` tab visit shows the Total elapsed banner first — that's the prominence the user asked for.

The theme toggle cycles `light → dark → auto` and persists across visits.

## 4. Data / Schema deltas

None. The `/api/data` shape from `functions/api/data.js` is unchanged; this is a pure presentation-layer redesign. Per-spec JSONL events are read exactly as they are today (the in-flight timeline already consumes them).

## 5. Out of scope

- **Spec-creation lifecycle hooks** (the multi-rail extension of `stages.py` discussed in the initial conversation: emitting events from `/spec-draft`, `/spec-queue`, `/spec-promote`). The Spec creation tab in §2.4 ships with no stage-timeline card precisely because those events do not exist yet. Separate future spec.
- **Unfolded stage timeline for the spec-creation rail.** User explicitly said "just for the development." The Spec creation tab shows drafts + activity feed only.
- **Changes to `functions/api/data.js`** or the data payload shape. The redesign uses the same fields the bootstrap already fetches.
- **Changes to `/dev-next`, `/spec-queue`, `/spec-promote`, `/spec-draft`** or the event-emission contract. No new event step names introduced.
- **Changes to `design-system/assets/styles/tokens-and-primitives.css`** or `composed-components.css`. Theme shim is dashboard-local only.
- **GitHub Pages workflow** (`.github/workflows/dashboard.yml`) and Cloudflare Pages build config. Render call signature is unchanged.
- **Per-spec detail pages** (`render_spec_page()` at render_dashboard.py:1006 and `render_draft_page()` at render_dashboard.py:1052). Out-of-scope refresh; only `render_index()` and its helpers change.

## 6. Test plan

- [ ] **Snapshot test of `render_index()` in idle mode** — given a fixture with no in-flight specs, the output contains: exactly one `.callout-strip` element, exactly one `.tabs` element with 4 buttons, four `<section class="tab-panel">` elements (one with `aria-hidden="false"`).
- [ ] **Snapshot test of `render_index()` in in-flight mode** — given a fixture with one `status: in_progress` spec, the Now tab's panel contains a `.stage` list with 11 `<li>` items, no `aria-hidden`/`details` collapse wrapper around it (i.e. expanded by default).
- [ ] **Total-elapsed banner math** — given a fixture of 5 deployed specs with known cycle times, the banner shows correct sum, correct mean (with outliers > 1h excluded), correct median (including outliers), and correct fastest/slowest spec ids.
- [ ] **Theme token shim** — a test loads `DASHBOARD_CSS`, asserts the presence of `[data-theme="light"]`, `[data-theme="dark"]`, and `[data-theme="auto"]` blocks, and asserts the `auto` block contains a `@media (prefers-color-scheme: dark)` nested rule.
- [ ] **Cycle-time chart bucket assignment** — given a list of cycle seconds `[300, 600, 1200, 1800, 2400]`, the rendered HTML applies the classes `.chart__bar--fast`, default, default, `.chart__bar--slow`, `.chart__bar--vslow` in that order.
- [ ] **Filter + search client behavior** (vitest under `tests/dashboard-bootstrap.test.js` per the spec-0161 stack) — applying a `bug` filter to a fixture of 8 specs (2 bugs, 6 others) reduces visible rows to 2; clearing it restores 8; typing "0156" in search narrows to specs whose number or title contains that substring.

## 7. Risks

- **Risk: theme flash on first paint.** If the bootstrap script reads localStorage *after* the page renders, the user sees a flash of the wrong theme. Mitigation: emit a tiny inline `<script>` in `<head>` (in `_html_head()` at render_dashboard.py:342) that synchronously reads `localStorage` and sets `data-theme` on `<html>` before the body paints. Keep that script under 5 lines; everything else can wait for the deferred bootstrap.
- **Risk: token shim drifts from `tokens-and-primitives.css`.** If the DS adds a new role (e.g. `--md-surface-7`) and the dashboard's theme shim doesn't re-project it, dark mode breaks silently for that role. Mitigation: shim re-projects only the roles the dashboard actually uses (an explicit allowlist in `DASHBOARD_CSS`). The list is documented in a comment block at the shim's location so future DS additions surface as an obvious gap. Accept that this is a maintenance cost.
- **Risk: tab-state regression for users who deep-link.** A user who bookmarks the current dashboard will land on the Now tab regardless of where they last were. We're intentionally not persisting tab state (§2.2). Mitigation: none needed — accepted behavior; matches the "read-only at-a-glance" framing.
- **Risk: cycle-chart axis loses meaning over time.** Once we accumulate 50+ deployed specs, "last 12" becomes an arbitrary window. Mitigation: keep it at 12 for now; the History tab is the durable record.
- **Risk: `render_index()` rewrite breaks the bootstrap client-server contract.** The server-rendered shell-only output (`--shell-only` flag, render_dashboard.py:881) must continue to match the regions the client paints. Mitigation: the test plan's first two checks assert the regions are still present in both modes.
- **Risk: parallel `/dev-next` cycles emit events that the new tabs misroute.** The Now tab feed must show dev-cycle events only; the Spec creation tab must show authoring events only. Mitigation: filter by event step name — the dev-cycle steps are exactly those in `STAGES` at `scripts/spec_lifecycle/stages.py:22` plus the spec-0163 informational steps in `TOLERATED_NON_STAGE_STEPS`; authoring steps right now are just `queued`. Hard-code the partition in the renderer.
