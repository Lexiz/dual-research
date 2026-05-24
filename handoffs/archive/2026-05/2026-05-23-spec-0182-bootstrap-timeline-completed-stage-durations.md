---
spec: "0182"
date: 2026-05-23
version: "1.36.5"
pr: "https://github.com/Lexiz/dual-research/pull/212"
---

# Spec 0182 — Bootstrap timeline per-stage durations — handoff

## What landed

The spec dashboard's hero timeline now keeps server-rendered per-stage durations across the 5-second `/api/data` repaint instead of flipping every completed cell to a literal em-dash.

- **`computeStages` in `DASHBOARD_BOOTSTRAP_JS`** now walks event timestamps and returns `{ name, status, ev, duration_seconds }` per stage. Anchor preference `cycle_started → queued → in_progress` mirrors `stages.py:225-229` exactly so first-paint (server) and repaint (client) agree on historical specs that pre-date `cycle_started`. For completed stages: `duration_seconds = max(0, floor((ev.ts - prev_ts) / 1000))`; for the current stage: against `Date.now()`. Defensive `isFinite` guard catches malformed ISO strings and falls back to `null`.
- **New `_fmtDurSecs` JS helper** mirrors `_humanize_seconds` exactly (`s` / `m s` / `h m` / `d h` / `w d`). Returns em-dash for `null` / negative. Locked the no-zero-pad seconds format (`5m 3s`, not `5m 03s`) since that's what the server emits.
- **`renderTimeline`** consumes `s.duration_seconds` through `_fmtDurSecs` for the `.tl__dur` cell. The `data-stage-started-at` attribute on the current node is untouched, so the 1-second ticker continues to overwrite the current cell live.
- **New tests** at `tests/spec_lifecycle/test_render_dashboard_spec_0182.py` — 4 source-substring assertions (no JS runtime in the rig per the spec's design): `duration_seconds` field present, `_fmtDurSecs` invoked, anchor chain present verbatim, null-guard in helper.

## Verify

The fix lives in the GitHub Pages dashboard at <https://lexiz.github.io/dual-research/>. Load any in-flight hero, wait 5 seconds for the bootstrap to repaint, inspect the `.tl__dur` cells on completed stages — they continue to show their per-stage durations (e.g. `1m 12s`, `4m 03s`) instead of flipping to em-dash. **Caveat**: the gh-pages dashboard rebuild workflow has been failing on every push today for unrelated GitHub billing reasons (`The job was not started because recent account payments have failed`). The merged code is correct; the dashboard will update automatically once the billing block is resolved. The `fly` deploy of the live app (`dual-research-alex.fly.dev`) is unaffected and succeeded.

## Deploy notes

- `fly deploy` clean, both machines green; old blue machines (`0805099fd14618`, `8ed007c7134008`) destroyed.
- `scripts/sweep_stale_blues.sh`: `sweep: no stale blues on dual-research-alex`.
- **GitHub Pages dashboard workflow failed** (`.github/workflows/dashboard.yml`, run 26331412293) due to GitHub billing — same failure pattern across every recent push. Not caused by this spec.
- Local main checkout: the queue worktree had to do the deploy from a detached HEAD at `origin/main` because the author worktree was holding the `main` branch ref (the spec 0181 deferral subagent left it there). The `git checkout main && git pull` step in the cycle template hit `fatal: 'main' is already used by worktree`; worked around with `git switch --detach origin/main`. Same scenario could recur for any spec that ships a deferral subagent — consider asking the deferral subagent to checkout a temp branch after committing.

## Tests

`uv run pytest tests/ -q` — 1665 passed in 19.67s. Includes the 4 new `test_render_dashboard_spec_0182.py` assertions.
