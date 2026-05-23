---
spec: "0185"
date: 2026-05-23
version: 1.36.8
pr: "https://github.com/Lexiz/dual-research/pull/215"
---

# Spec 0185 — Cycle-time chart Y-axis cap percentile-based — shipped

The Metrics-tab cycle-time line chart's hard-coded 60-minute Y-axis cap is
gone. Bootstrap repos with only sub-10m cycles now get readable headroom; mature
repos with outlier cycles clip the worst few against a nice-rounded p95 cap. The
spec-0177 baseline (cycles in the 10–60m range) is unchanged — the nice-rounded
p95 still lands at 60m there.

## What landed

- **[scripts/spec_lifecycle/render_dashboard.py:201](../scripts/spec_lifecycle/render_dashboard.py)** — three new module-level helpers near `_humanize_seconds`:
  - `_pick_cap(cycle_secs)` → `max(p95(cycle_secs), 10m)`. Uses `statistics.quantiles(..., n=20, method="inclusive")[18]` for p95.
  - `_nice_round_cap(secs)` → rounds up to next value in `{10, 15, 20, 30, 45, 60, 90, 120}` minutes. Clamps above 120m.
  - `_format_y_tick(cap, fraction)` → returns `"0"` for fraction 0, `"{N}m"` for integer-minute, `"{N}m {S}s"` otherwise.

- **[scripts/spec_lifecycle/render_dashboard.py:870](../scripts/spec_lifecycle/render_dashboard.py)** — `_render_cycle_time_chart` now picks `cap = _nice_round_cap(_pick_cap(cycle_secs))` instead of the literal `60 * 60`. The five hard-coded `<text>` Y-axis labels become a loop over `(1.0, 0.75, 0.5, 0.25, 0.0)` driven by `_format_y_tick`. The outlier-note caption was `"Outliers > 1h ({N}) clipped to the top."`; now it's `f"Outliers > {cap // 60}m ({N}) clipped to the top."` against the dynamic cap.

- **[design-system/SPEC.md:96](../design-system/SPEC.md)** — new "Cycle-time chart Y-axis cap (spec 0185)" sub-section under §2.1 documents the heuristic so future spec authors don't reverse-engineer the cap from code.

- **[tests/spec_lifecycle/test_render_dashboard_spec_0185.py](../tests/spec_lifecycle/test_render_dashboard_spec_0185.py)** — 14 new tests:
  - 8 helper unit tests covering `_pick_cap` (floor / p95 / empty / single-value), `_nice_round_cap` (rounding cases + 120m clamp), `_format_y_tick` (zero / integer-minute / sub-minute remainder).
  - 5 `_render_cycle_time_chart` integration tests covering the three repo shapes from spec §4 (bootstrap sub-10m, outlier-laden, 60m baseline), the dynamic outlier-note prose, and a regression guard on the label `text-anchor` + `x` offset for visual parity. Full suite: 1690 passed.

- **CHANGELOG / version** — `1.36.7` → `1.36.8` (PATCH per refactoring type).

## Live smoke

```
$ curl -sS -o /dev/null -w "%{http_code}\n" https://dual-research-alex.fly.dev/
200
```

The live dashboard's cycle-time chart on `/#/metrics` now renders against the
data-driven cap — for this repo (cycles spread across the 10–60m range) the cap
still nice-rounds to 60m, so visually the chart is unchanged. The behaviour
divergence kicks in on bootstrap or outlier-heavy repos.

## Deploy notes

- `fly deploy` swapped cleanly on the first attempt. Bluegreen stopped+destroyed
  two stale blues (`781e622b126998`, `286d062c571d08`) before bringing the new
  group up.
- Post-deploy `scripts/sweep_stale_blues.sh`: `sweep: no stale blues on dual-research-alex`.
- Image: `dual-research-alex:deployment-…` running on two machines.

## What this DOES NOT do

- **Add a separate outlier chart.** Out of scope per spec §5. The outliers still
  render at the top of the same chart with a count annotation.
- **Add per-spec-type Y-axis caps.** Out of scope; the by-type bar chart already
  splits by type via its own axis treatment.
- **Introduce browser-side dynamic re-scaling.** The chart is server-rendered
  SVG; no JS-side cap recompute on the client.
- **Switch to a logarithmic axis.** Considered and rejected in spec §5.

The squash-merge of PR #215 was preceded by a force-with-lease push on the
feature branch after rebasing onto an advancing main (the `--push-to-main`
event commits had moved main forward while the branch was open). The rebase
conflict was append-only on `dashboard/events/0185.jsonl`; resolved by keeping
both sides' line additions.
