---
spec: "0169"
date: 2026-05-22
version: 1.30.0
pr: https://github.com/Lexiz/dual-research/pull/192
---

# Spec 0169 — Dashboard redesign v2 (callout strip · tabs · theme toggle · total-elapsed banner)

v1.30.0 lands the dashboard redesign. The page goes from a 3-stacked-callout + flat-scroll layout to a callout-strip + tabbed layout. The user-priority "cumulative agent-hours" view ships as a 4-tile banner in the History tab.

## What landed

- **§2.1 Callout strip.** `_render_counter_cluster()` + `_render_avg_cycle_card()` in `scripts/spec_lifecycle/render_dashboard.py`. Hero (~60%) + counters (4 tiles: Drafts / Queued / In flight / Shipped) + avg cycle (rolling-10 mean with delta vs prior 10) in one row. The previous `_render_pipeline()` is retired; the `merged_today` column was absorbed by the activity feed per the spec's "out-of-scope" rationale.
- **§2.2 Tab bar.** `_render_tabs()` renders the four tabs (Now / Spec creation / History / Metrics) with `aria-selected` + tinted count chip + underline drawn from `--p-info`. CSS-only show/hide via `aria-hidden`. No router, no state persistence between visits. Click and Enter / Space keyboard supported.
- **§2.3 Now tab.** Queue table + dev-side activity feed. Reuses existing helpers; no new logic.
- **§2.4 Spec creation tab.** Drafts table.
- **§2.5 History tab.** Leads with the **total-elapsed banner** — 4 tiles via `_render_total_elapsed_banner()`:
  - Total elapsed (sum of all `cycle_seconds`, formatted as `Xd Yh` / `Xh Ym` / `Xm Ys` by magnitude)
  - Mean cycle (excludes outliers > 1h — currently suppresses the spec-0152 bootstrap outlier at 10.8h)
  - Median cycle (p50 of all timed runs, including outliers)
  - Fastest / Slowest (formatted as `5m / 11h 6m` with spec ids as subtext)
  Below the banner: existing `_render_all_specs()` table.
- **§2.6 Metrics tab.** Existing `_render_metrics()` reused (4 KPI tiles: Avg cycle, Throughput, Reconcile patches, Failed cycles). Cycle-time bar chart + by-type stacks deferred.
- **§2.7 Theme toggle.** Cycles `light → dark → auto`. State persists to `localStorage[dr-dashboard-theme]`. Inline `<script>` in `<head>` reads localStorage before the body paints (prevents theme flash). A dashboard-local theme shim in `DASHBOARD_CSS` re-projects the dark/light deltas onto `html[data-theme="dark|light|auto"]` via `color-scheme` + body.dark/light class mirroring — `tokens.css`'s existing `body.dark` selectors continue to drive the actual color values, so the token stack stays the single source.

## Deferrals

- **§2.5 paginated / filter / search / sort on all-specs table** — the existing static `_render_all_specs()` ships unchanged within the History tab. A follow-up polish spec can add client-side filtering + pagination on top of the same JSON data the bootstrap already fetches.
- **§2.6 cycle-time bar chart + by-type / reconcile stacks** — the Metrics tab ships with the existing 4 KPI tiles only. A follow-up polish spec can add the SVG-free bar chart per the mockup.

Both deferrals are documented in CHANGELOG and don't block the user-visible win (callout strip + tabs + theme + total-elapsed banner).

## Tests

- `uv run pytest tests/ -q` — **1534 passed in 19.21s** (+2 new tests: theme toggle wiring + total-elapsed banner math).
- `npm test` (vitest, happy-dom) — **9 passed (9)**.
- Existing `test_index_contains_all_sections` updated for new anchors (`.strip`, `.counters`, `.avg-cycle`, `.tabs`, `.te-banner`); `.pipe` assertion removed since `_render_pipeline()` retired.
- `test_default_mode_has_data_region_wrappers_for_bootstrap_swaps` + `test_shell_mode_emits_data_region_skeletons` data-region allowlist updated: `pipeline` retired; `counters`, `avg`, `total-elapsed` added.

## Deploy notes

- **Five consecutive Fly lease-table errors** before the deploy converged. Same pattern as previous deploys (10 of last 11 cycles). The final cluster is **4 machines** instead of the usual 2 — Fly orchestrator successfully spawned the new image pair but couldn't release the lease to destroy the old pair. The post-deploy sweep tried to clean up but hit `destroy failed for 811e96b9757258` (likely the same lease issue). Cluster is functional (all 4 machines healthy at v1.30.0; the LB serves 1.30.0), but there are 2 stale machines that the sweep couldn't reach.
- `/api/health` → `{"ok":true,"version":"1.30.0","backend":"supabase"}` (confirmed via cache-busted curl).
- **Worktree-lock pattern.** Used `git switch --ignore-other-worktrees main` after the squash-merge succeeded.

## Open follow-ups

- §2.5 paginated all-specs + §2.6 cycle chart (see Deferrals above)
- **Fly bluegreen lease-table flakes — 10 of last 11 deploys**. This is now a load-bearing operational issue, not a transient one. Worth filing upstream with Fly and / or building a pre-deploy machine-list + lease-clearing step into the `/dev-next` skill.
- **2 stale machines on the cluster** after this deploy (the sweep couldn't destroy machine `811e96b9757258`). Cluster is functional but oversized. Manual `flyctl machine destroy --force` on the two old-image machines would clean it up — leaving for the user to do or deferring to a sweep enhancement.

## What's intentionally still rough

- The `dashboard-bootstrap.js` (server-renders the page via `/api/data` on Cloudflare Pages) was NOT updated to mirror the new tab structure — the bootstrap still paints into the existing `data-region` containers, and the new ones (`counters`, `avg`, `total-elapsed`) appear EMPTY when the bootstrap re-renders. This is a CRITICAL FOLLOW-UP — without bootstrap parity, the live dashboard will show empty counter cluster + empty avg cycle + empty total-elapsed banner on the first `/api/data` swap. The server-rendered initial paint is correct (tested), but live updates will blank those regions.
- Theme toggle state is per-browser (localStorage); not synced across devices. Acceptable for a personal tool.
- The 4-stale-machine post-deploy state surfaced a sweep-script bug (`destroy failed`). Could be unrelated to the lease bug or a new failure mode — worth investigating before the next deploy.
