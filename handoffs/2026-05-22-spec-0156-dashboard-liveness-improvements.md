---
spec: "0156"
date: 2026-05-22
version: 1.20.0
pr: "https://github.com/Lexiz/dual-research/pull/179"
---

# Handover — Spec 0156 — Dashboard live-ness: cycle_started anchor, auto-refresh, live ticker, deploy cleanup (v1.20.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#179](https://github.com/Lexiz/dual-research/pull/179)
- **Merge commit:** `afce600`
- **Cycle time:** ~18 minutes (started 13:26:37Z, deployed 13:45:00Z)

## What landed

### `cycle_started` anchor (`scripts/spec_lifecycle/stages.py`)

- `TOLERATED_NON_STAGE_STEPS` adds `cycle_started`.
- `compute_stages`'s anchor preference is now `cycle_started` → `queued` → `in_progress`. Pre-flight / Read handoff / Read spec stages get real positive durations on the in-flight hero instead of being clipped to 0s by the prior race (where `/dev-next` step 12 emitted `in_progress` alongside the buffered early events, making `preflight_ok_ts - in_progress_ts` negative).
- `StageState` picks up a `started_at` field — the wall-clock instant each stage began, equal to the previous stage's event timestamp (or the cycle anchor for stage 0). Used by the live ticker.
- Host-side: `~/.claude/skills/dev-next/SKILL.md` step 1 now emits `cycle_started` right after `git pull --ff-only`. Spec 0156 emitted it for its own cycle (`dashboard/events/0156.jsonl`).

### Browser auto-refresh (`scripts/spec_lifecycle/render_dashboard.py`)

- `_html_head` now ships `<meta http-equiv="refresh" content="60">`. Every dashboard page reloads itself every 60s. Long enough not to interrupt mid-scroll reads, short enough that the dashboard feels current.

### Live elapsed ticker (`dashboard/site/dashboard-live.js`, new)

- ~50 lines, no external deps. JS mirror of the Python `_humanize_seconds` formatter (`Xs`, `Xm Ys`, `Xh Ym`, `Xd Yh`).
- The in-flight hero's `ELAPSED` display now carries `data-cycle-started-at` (the cycle_started event timestamp), and the current stage's duration cell carries `data-stage-started-at` (the previous stage's event timestamp). The JS runs `setInterval(tick, 1000)` and rewrites their `textContent` from `Date.now()`.
- Honors `prefers-reduced-motion: reduce` — script no-ops if the user has reduced motion enabled, leaving the server-side static timing in place.
- New `DASHBOARD_LIVE_JS` constant in the renderer; `main()` writes `dashboard-live.js` to the output dir alongside `dashboard.css`.

### Deploy-pages cleanup (`.github/workflows/dashboard.yml`)

- The `deploy` job using `actions/deploy-pages@v4` was removed.
- **Path A was unavailable.** `gh api -X POST /repos/Lexiz/dual-research/pages -f build_type=workflow` returns **422** "Your current plan does not support GitHub Pages for this repository" — the repo is private and the account's plan doesn't include Pages on private repos.
- **`https://lexiz.github.io/dual-research/` was returning 404** before this change. The dashboard URL referenced in handoffs and `CLAUDE.md` isn't actually serving content — it never was, post-private-flip. The "8/8 workflow runs failing at deploy-pages" the spec's evidence cited was the symptom of this deeper config issue, not the cause.
- **Path B (the fallback) landed.** The render output is now uploaded as a generic `dashboard-site` workflow artifact (14-day retention) instead of via `actions/upload-pages-artifact`. Downloadable from the workflow run UI for inspection.
- **Follow-up worth queuing:** restore proper hosting for the rendered dashboard. Options: serve from the fly.io app's `/dashboard` route; switch the repo to public; or accept dashboard-as-workflow-artifact and stop linking `lexiz.github.io` in `CLAUDE.md`. Recommended path TBD.

## Tests

- `tests/spec_lifecycle/test_stages.py` — three new functions: `test_cycle_started_anchor_gives_real_preflight_duration`, `test_anchor_fallback_to_queued_for_legacy_specs`, `test_stage_started_at_exposed_on_state`.
- `tests/spec_lifecycle/test_render_dashboard.py` — four new functions: meta-refresh present, dashboard-live.js script tag, in-flight hero emits both data attributes with ISO 8601 timestamps, `main` writes `dashboard-live.js` to the output dir.
- `uv run pytest tests/ -q` — **1485 passed** (1478 prior + 7 new).
- Manual smoke — `render_dashboard --repo-root . --out /tmp/dr-dash-0156` rendered 149 specs + 4 drafts; in-flight hero shows `data-cycle-started-at="2026-05-22T13:26:14+00:00"` matching the cycle's `cycle_started` event timestamp.

## Deploy notes

- Same transient Fly machines-API timeout we hit on 0153's first deploy: rolling deploy reached both machines (v247, v248 on `deployment-01KS7YFV1E5A45TVC1ZVGXT196` running v1.20.0) but the CLI lost connectivity to `api.machines.dev` before observing the second machine's health-check pass. The image and machines were actually fine — `curl https://dual-research-alex.fly.dev/api/health` returns `{"ok":true,"version":"1.20.0","backend":"supabase"}`. The machines were auto-stopped (Fly's idle-stop mode) when I checked status; the health probe woke them and they came up cleanly.
- **No retry needed this time** — the deploy actually succeeded despite the CLI's "Unrecoverable error" message.

## Queue at handoff

- **0157** — `/spec-queue` auto-decomposition (queued).
- **0158** — deferred-spec subagent in `/dev-next` (queued).

Both were committed to main by a parallel author session while 0156 was in flight, then landed via the same `/spec-queue` push that caught the merge race on this PR. Per `feedback_pause_between_specs`: this cycle stops here. Next `/dev-next` (or `/dev-queue-run` to drain both) is on the user.

## File map

```
# In-repo (this PR)
scripts/spec_lifecycle/stages.py             # anchor order + StageState.started_at
scripts/spec_lifecycle/render_dashboard.py   # meta refresh, data attrs, DASHBOARD_LIVE_JS
.github/workflows/dashboard.yml              # deploy-pages job removed
tests/spec_lifecycle/test_stages.py          # 3 new tests
tests/spec_lifecycle/test_render_dashboard.py # 4 new tests
CHANGELOG.md                                  # [1.20.0] section
pyproject.toml, src/dual_research/__init__.py # 1.20.0
specs/0156-dashboard-liveness-improvements.md # status: deployed
dashboard/events/0156.jsonl                   # full event stream incl cycle_started
handoffs/2026-05-22-spec-0156-...md           # this file

# Host-side (not in repo)
~/.claude/skills/dev-next/SKILL.md           # step 1 emits cycle_started
```

## Open follow-ups (not in scope for 0156)

- **Dashboard hosting is broken.** `lexiz.github.io/dual-research/` is dead. CLAUDE.md and prior handoffs still link to it. Decide on a hosting path (fly.io `/dashboard` route, public repo, or stop linking) and update the references.
- **Per-stage `*_started` / `*_done` event pairs** would eliminate the bursty-0s case for handoff_read/spec_read but require restructuring `/dev-next`'s emission cadence. Spec 0156 §5 lists this explicitly out of scope; flag for a future spec if the bursty case becomes annoying.
- **`session-title-stamping.py` fallback path.** When `$CLAUDE_SESSION_ID` isn't exported (which is the case in `/dev-next` invocations), the helper falls back to "most-recently-modified `local_*.json`", which can stamp the wrong session if multiple are open. The 0156 in-flight stamp worked (visible in the chat), but it's racey.
