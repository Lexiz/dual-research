---
kind: dev
spec: "0185"
slug: cycle-time-chart-percentile-y-axis-cap
title: "Refactor: cycle-time line chart Y-axis cap from fixed 60m to a percentile-based / auto-ranged cap"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: 1.36.8
status: deployed
queue_position: 2
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T22:00:00Z"
started_at: "2026-05-23T12:14:09Z"
merged_at: "2026-05-23T12:20:22Z"
deployed_at: "2026-05-23T12:30:50Z"
pr: "https://github.com/Lexiz/dual-research/pull/215"
handover: "handoffs/2026-05-23-spec-0185-cycle-time-chart-percentile-y-axis-cap.md"
failure_step: ""
source_session: deferred-from-0177
promoted_from_draft: ""
---

# Spec 0185 — Refactor: cycle-time line chart Y-axis cap from fixed 60m to a percentile-based cap

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** PATCH — internal restructure of the Y-axis cap heuristic, no behavior change for repos with cycles in the 0–60m range.
> **Evidence:** Spec 0177 handoff `## Deferred during implementation` fourth bullet — [handoffs/2026-05-22-spec-0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md:43](handoffs/2026-05-22-spec-0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md:43). The implementer noted: *"chose 60m (per mockup's '20m' axis bumped up to absorb queue-drain outliers in the 30–60m range). Repos with no outliers but mostly sub-10m cycles render with most points clustered at the bottom of the chart. Auto-ranging or a percentile-based cap (clip at p95) is a tunable that's deferred."*

---

## 1. Current state

The cycle-time line chart on the Metrics tab caps its Y-axis at a hard-coded 60 minutes. [scripts/spec_lifecycle/render_dashboard.py:871](scripts/spec_lifecycle/render_dashboard.py:871):

```python
cap = 60 * 60  # 60 minutes; outliers render at the cap and are annotated.
```

This cap is then used to scale every plotted point into the chart area via the `_y` helper at [scripts/spec_lifecycle/render_dashboard.py:881-882](scripts/spec_lifecycle/render_dashboard.py:881), and to label the Y-axis ticks at `60m / 45m / 30m / 15m / 0` via the literal text elements at [scripts/spec_lifecycle/render_dashboard.py:937-941](scripts/spec_lifecycle/render_dashboard.py:937).

The pain:

- **Bootstrap repos cluster at the floor.** A new repo whose cycles are all sub-10m renders ~80% of the chart vertical space as empty whitespace. The actual variation between, say, a 4m cycle and an 8m cycle is barely visible — both points sit in the bottom sixth of the chart.
- **Mature repos with a single outlier still lose resolution.** A repo whose median is 12m but has one 55m queue-drain cycle uses about a fifth of the chart's vertical range to show 22 of 23 points, while one outlier occupies the rest. The mockup pre-bake at "20m" was tuned to the mature-repo with rare outliers — neither the bootstrap case nor the heavy-outlier case is well served.
- **Hard-coded label text.** The five Y-axis labels (`60m / 45m / 30m / 15m / 0`) are hard-coded strings, so even if the cap changes the labels don't follow. They are co-located at [scripts/spec_lifecycle/render_dashboard.py:937-941](scripts/spec_lifecycle/render_dashboard.py:937) inside the SVG emit.

The cap was a defensible compromise at spec 0177 implementation time but the handoff explicitly named "percentile-based cap (clip at p95)" as the right follow-up.

## 2. Target state

A small helper inside `_render_cycle_time_chart` that picks the Y-axis cap dynamically from the data, and a label-generator that derives the five gridline labels from the chosen cap. The helper:

- Picks `cap = max(p95(cycle_secs), MIN_CAP_SECONDS)` where `MIN_CAP_SECONDS = 10 * 60` (10 minutes). This keeps the chart readable on bootstrap repos (always at least 10m of vertical headroom) and uses p95 for repos with enough data to clip just the worst few outliers.
- Rounds the chosen cap *up* to the next nice round number — one of `[10, 15, 20, 30, 45, 60, 90, 120]` minutes — so the axis labels stay readable. Function: `_nice_round_cap(secs) -> int`.
- The label generator emits the five gridline texts as `_format_y_tick(cap, fraction)` where fraction ∈ `{0, 0.25, 0.5, 0.75, 1.0}`. The format is `"{N}m"` for integer-minute caps and `"{N}m {S}s"` for non-round fractions if any — but with the nice-rounding the fractions are always integer-minute, so the format simplifies to `"{N}m"`.

Anchor changes:

- [scripts/spec_lifecycle/render_dashboard.py:871](scripts/spec_lifecycle/render_dashboard.py:871) — replace the hard-coded `cap = 60 * 60` with `cap = _nice_round_cap(_pick_cap(cycle_secs))`.
- [scripts/spec_lifecycle/render_dashboard.py:937-941](scripts/spec_lifecycle/render_dashboard.py:937) — replace the five hard-coded label `<text>` elements with a loop that emits one `<text>` per gridline using `_format_y_tick(cap, fraction)`.
- The `outlier_count` computation at [scripts/spec_lifecycle/render_dashboard.py:872](scripts/spec_lifecycle/render_dashboard.py:872) keeps the same shape (`sum(1 for v in cycle_secs if v > cap)`) but now reads against the dynamic cap. The caption text at [scripts/spec_lifecycle/render_dashboard.py:916-918](scripts/spec_lifecycle/render_dashboard.py:916) — `"Outliers > 1h (N) clipped to the top."` — must be reworded to use the dynamic cap (e.g. `f"Outliers > {cap // 60}m ({N}) clipped to the top."`).

No DS change, no token change, no `composed-components.css` / `components.css` edit. The chart card chrome is unaffected.

## 3. Stepwise migration

Each step independently shippable / revertable.

- **Step 1:** Add `_pick_cap`, `_nice_round_cap`, `_format_y_tick` as module-level helpers inside [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py) (near `_humanize_seconds` at the top of the helpers block, around line 800). Each helper gets a docstring and a unit test. The cycle-time chart still uses the hard-coded 60m at this point — these helpers are dead code. Verifies: helper unit tests pass; the dashboard render is byte-identical to pre-step. (Smoke: diff the rendered HTML against a `git show HEAD:`-style baseline before/after.)
- **Step 2:** Switch [scripts/spec_lifecycle/render_dashboard.py:871](scripts/spec_lifecycle/render_dashboard.py:871) (`cap = 60 * 60`) to `cap = _nice_round_cap(_pick_cap(cycle_secs))`. The five `<text>` labels at [scripts/spec_lifecycle/render_dashboard.py:937-941](scripts/spec_lifecycle/render_dashboard.py:937) become a `for` loop driven by `_format_y_tick`. The outlier-note text at [scripts/spec_lifecycle/render_dashboard.py:916-918](scripts/spec_lifecycle/render_dashboard.py:916) gets templated against the dynamic cap. Verifies: the spec-0177 test that asserts the chart card renders still passes; a new test (§4) asserts the cap adapts to fixture data; visual diff against the live dashboard.
- **Step 3:** Document the new behaviour in [design-system/SPEC.md](design-system/SPEC.md) §2.1 (Chart palette / cycle-time chart sub-section if one exists; otherwise add one). One paragraph: "Cycle-time chart Y-axis caps at `max(p95, 10m)` rounded up to the nearest nice value in `{10, 15, 20, 30, 45, 60, 90, 120}` minutes. Outliers above the cap render at the top of the chart with a count annotation in the caption."

## 4. Behavior preservation

- [ ] Existing test `test_metrics_tab_renders_cycle_time_chart` (or whichever spec-0177 test covers chart card presence) at [tests/spec_lifecycle/test_render_dashboard_spec_0177.py](tests/spec_lifecycle/test_render_dashboard_spec_0177.py) still passes (covers chart-card structural presence — unchanged).
- [ ] New parity test `test_cycle_time_chart_cap_picks_p95_with_floor` — fixture with cycle times `[2m, 3m, 4m, 5m, 6m]` (all sub-10m): asserts the rendered SVG contains `"10m"` as the top Y-axis label (because `MIN_CAP_SECONDS = 600` wins over p95 of `~6m`). Currently the rendered SVG contains `"60m"`.
- [ ] New parity test `test_cycle_time_chart_cap_clips_outliers_above_p95` — fixture with cycle times `[5m] * 19 + [55m] * 1` (one outlier well above p95): asserts the rendered cap is `15m` or `20m` (a nice-rounded p95) and the outlier-note text reports 1 clipped outlier.
- [ ] New parity test `test_cycle_time_chart_cap_for_60m_repos_unchanged` — fixture with cycle times spread `[10m, 20m, 30m, 40m, 50m, 60m]` evenly: asserts the cap is `60m` (so the behaviour for the spec-0177 baseline use case is preserved — no regression for the data the original 60m was tuned for).

## 5. Out of scope

**Explicit: this spec does NOT add any new feature** — no new feature lands here. Any feature work that depends on this refactor lives in a follow-up spec.

- A second chart that shows the *outlier* cycles separately (full-range, no cap). Would be a new chart card, not a tweak to this one.
- Per-spec-type Y-axis caps (e.g. one cap for `bug` cycles, another for `new-feature`). The by-type bars at [scripts/spec_lifecycle/render_dashboard.py:1796](scripts/spec_lifecycle/render_dashboard.py:1796) already split by type; a separate per-type line chart is out of scope.
- Browser-side dynamic chart re-scaling (e.g. user drags a slider to set the cap). The chart is server-rendered SVG; interactivity is not introduced here.
- Logarithmic Y-axis. Considered and rejected — log axes are less readable for time-series with a narrow real range. Linear with a smart cap is the right primitive.
- Configurable threshold via env var or repo config. The percentile + nice-round heuristic is general enough that no per-repo tuning should be needed.

## 6. Risks

- **Hidden behavior depending on internals.** Any external test or screenshot that asserted the specific text "60m" appears on the rendered chart would break. Mitigation: grep [tests/](tests/) for `"60m"` and `60 \* 60` and `var\(--chart` — the only references are inside the renderer itself. No external consumer pins the cap.
- **Performance regression.** Computing p95 over up to 22 values is O(n log n) sort or O(n) via `statistics.quantiles`. Negligible — runs once per dashboard render, dominated by the surrounding HTML emit cost.
- **Missed call site.** Only one cap exists today (the cycle-time line chart). The `_compute_stage_durations` helper at [scripts/spec_lifecycle/render_dashboard.py:1796+](scripts/spec_lifecycle/render_dashboard.py:1796) and the throughput-per-week bars use their own scales (per-bar normalisation, no global cap), so no other site needs updating.
- **Label text-anchor.** The five Y-axis labels are right-aligned at `text-anchor="end"` per [scripts/spec_lifecycle/render_dashboard.py:935-936](scripts/spec_lifecycle/render_dashboard.py:935). A loop-emitted set must preserve the same anchor + the same x-offset (`pad_l - 6`) for visual parity. The migration in Step 2 must keep these attributes; locked by a unit test that snapshot-compares the rendered label block against the pre-refactor output for a 60m cap fixture.
- **Outlier-note prose drift.** The caption sentence at [scripts/spec_lifecycle/render_dashboard.py:916-918](scripts/spec_lifecycle/render_dashboard.py:916) currently says "Outliers > 1h" — a constant string. After the refactor it becomes dynamic. Any external doc that quotes the constant string would drift. Verified: no doc quotes it. Mitigation: keep the same overall sentence structure ("Outliers > Xm (N) clipped to the top.") so the change is purely the number, not the grammar.
- **Bootstrap-repo edge case where p95 = 0.** If a repo has only one deployed cycle, `_pick_cap` reduces to `max(value, MIN_CAP_SECONDS)` which is fine. If a repo has zero deployed cycles, the chart short-circuits to its empty-state path at [scripts/spec_lifecycle/render_dashboard.py:862-868](scripts/spec_lifecycle/render_dashboard.py:862) before the cap is ever computed — no risk.
