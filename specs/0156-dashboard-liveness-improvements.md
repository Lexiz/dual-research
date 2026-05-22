---
kind: dev
spec: "0156"
slug: dashboard-liveness-improvements
title: Dashboard live-ness — cycle-started anchor, browser auto-refresh, live elapsed ticker, deploy-pages cleanup
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.20.0
status: queued
queue_position: 1
depends_on: []
complexity: S
created: 2026-05-22
queued_at: 2026-05-22T13:12:40Z
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: orchestrator-hardening-2026-05-22
promoted_from_draft: ""
---

# Spec 0156 — Dashboard live-ness — cycle-started anchor, browser auto-refresh, live elapsed ticker, deploy-pages cleanup

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** MINOR — adds two visible UI capabilities (auto-refresh + live ticker), plus a small timing-bug fix and a workflow cleanup. No breaking changes.
> **Evidence:** screenshot of 0154 in-flight hero showing Pre-flight / Read handoff / Read spec all at 0s (real durations were minutes); `gh run list --workflow dashboard.yml` shows 8/8 most recent runs failing at deploy-pages with `HttpError: Not Found`.

---

## 1. Context

Two distinct dashboard quality issues surfaced while watching `/dev-next` 0154 in flight:

- **Timing display is wrong.** Stage durations show 0s for Pre-flight, Read handoff, and Read spec even though they took real wall-clock time. Reconcile correctly showed 1m 1s. Root cause: [`stages.py:170-172`](/Users/alexlisitzky/dual-research-author/scripts/spec_lifecycle/stages.py) picks `in_progress` as the cycle anchor, but `in_progress` is *emitted last* in /dev-next step 12 (alongside the buffered preflight_ok/handoff_read/spec_read/reconcile_complete events). For spec 0154, `preflight_ok` was at 12:56:17Z and `in_progress` at 12:57:39Z — `preflight_ok_ts - in_progress_ts` is negative, then clipped to 0 by `max(0, …)` at [`stages.py:200`](/Users/alexlisitzky/dual-research-author/scripts/spec_lifecycle/stages.py). Subsequent same-second emissions (handoff_read, spec_read) inherit that 0 and produce 0 deltas themselves.
- **Live-ness is poor.** The hero shows "3m 3s ELAPSED" frozen at workflow-render time. Browser doesn't reload, so the user manually refreshes — and when they do, the dashboard often lags behind `origin/main`. Compounding: [`.github/workflows/dashboard.yml`](/Users/alexlisitzky/dual-research-author/.github/workflows/dashboard.yml) deploy-pages step has 404'd on 8/8 recent runs (`HttpError: Not Found - Ensure GitHub Pages has been enabled`). Render step succeeds (HTML built into `dashboard/site/`), but the deploy step fails. Pages still serves *something* (likely legacy branch-source mode from `main` root) — that's the path keeping the dashboard alive despite the workflow's red status.

The user explicitly framed this as "minimum effort" work. Out of scope: server-side push (SSE/WebSocket from the fly.io app), incremental event-per-commit pushing (rejected as too much workflow noise), and migrating the renderer off GitHub Pages.

## 2. Proposed change

Four discrete fixes in one spec.

### 2.1 — Anchor fix in `scripts/spec_lifecycle/stages.py`

- Update the anchor preference at [`stages.py:170-172`](/Users/alexlisitzky/dual-research-author/scripts/spec_lifecycle/stages.py): `cycle_started` → `queued` → `in_progress`. The `cycle_started` event becomes the canonical "agent began work" marker.
- Update [`stages.py:39`](/Users/alexlisitzky/dual-research-author/scripts/spec_lifecycle/stages.py) `TOLERATED_NON_STAGE_STEPS` to include `cycle_started`.
- Emit `cycle_started` in /dev-next step 1, right after `git pull --ff-only` lands (per spec 0154's step-1 fix). One-line `append_event` call.
- Legacy specs (without `cycle_started`) fall back to `queued` — still better than `in_progress` because queued is the earliest timestamp. Pre-flight duration for legacy specs becomes (preflight_ok_ts - queued_ts), which conflates queue-dwell time with execution but is non-zero and broadly correct.
- The bursty same-second emission case (handoff_read + spec_read in the same `append_event` burst) remains as 0s — that's accurate at 1-second resolution and acceptable. Mentioned in §5 (out of scope to fix here).

### 2.2 — Browser auto-refresh in `scripts/spec_lifecycle/render_dashboard.py`

- Inject `<meta http-equiv="refresh" content="60">` into the `<head>` of generated dashboard pages (`index.html`, `spec-NNNN.html`, `draft-NNN.html`).
- 60 seconds chosen as a balance: long enough that mid-scroll users aren't disrupted, short enough that the dashboard feels current.

### 2.3 — Live elapsed ticker

- For the in-flight hero, render the current stage's start timestamp as a `data-stage-started-at` attribute on the relevant DOM element. Render the cycle start timestamp as `data-cycle-started-at` on the hero's `ELAPSED` display.
- Ship a small JS asset at `dashboard/site/dashboard-live.js` (~30 lines) that runs `setInterval(updateElapsed, 1000)` and rewrites the text content of any element with those data attributes using `Date.now() - dataset.stageStartedAt`. Formats as `Hh Mm Ss` matching the existing server-side renderer.
- Add `<script src="dashboard-live.js" defer></script>` to the hero template.
- Honor `prefers-reduced-motion: reduce` — script no-ops if matchMedia matches. Reduced-motion users see static server-side timing.

### 2.4 — Deploy-pages cleanup

- Inspect [`.github/workflows/dashboard.yml`](/Users/alexlisitzky/dual-research-author/.github/workflows/dashboard.yml) (currently has both a `render` job uploading artifact and a `deploy` job using `actions/deploy-pages@v4`).
- Two paths, decide at implementation time based on what `gh api /repos/Lexiz/dual-research/pages` returns (currently returns 404 — meaning Pages-from-Actions is *not* enabled; legacy mode must be doing the serving):
  - **Path A (recommended):** Enable Pages-from-Actions in the repo settings (one-time click at `github.com/Lexiz/dual-research/settings/pages`, switch source to "GitHub Actions"). Then the deploy job succeeds, serving the rendered `dashboard/site/` artifact via the proper Pages CDN. Requires user action — flag clearly in implementation handoff.
  - **Path B (fallback if user can't/won't change settings):** Remove the `deploy` job from `dashboard.yml`. Pages keeps serving from legacy source. Workflow runs go green. Slightly less ideal serving infrastructure but no visible difference.
- Implementer picks Path A by default; falls back to Path B if Path A requires unavailable settings access during the cycle.

## 3. UX / Behavior

- Hero "ELAPSED" counter ticks every second without page reload.
- In-flight stage "duration" ticks every second.
- Browser auto-reloads every 60s, picking up new spec events without user intervention.
- Pre-flight, Read handoff, Read spec stages show real durations (non-zero when work was performed).
- Dashboard workflow runs show green at the deploy step.
- Reduced-motion users see static server-side timings (no JS ticker).

## 4. Data / Schema deltas

No schema changes. One new event type: `cycle_started`. Event sidecar format unchanged (still `{"ts": "...", "step": "cycle_started", "data": {}}`). No migration needed — older specs without `cycle_started` fall back gracefully via the anchor-preference order in §2.1.

## 5. Out of scope

- **Server-side live push** (SSE / WebSocket from the dual-research fly.io app). Different effort tier. User explicitly framed this spec as minimum-effort.
- **Per-event commit + push** (each `append_event` triggers its own workflow run). Rejected during ideation as ~10× workflow noise for marginal gain. Browser auto-refresh (§2.2) closes most of the perceived lag at zero workflow cost.
- **Migrating dashboard rendering off GitHub Pages** entirely (e.g. serving from the fly.io app's `/dashboard` route). Bigger lift.
- **Sub-second event timestamps.** Current 1s resolution is sufficient for staged work; bursty same-second emissions stay at 0s and that's accurate at this resolution.
- **Per-stage `*_started` / `*_done` event pairs.** Would eliminate the bursty-0s case for handoff_read/spec_read but requires reshaping /dev-next's emission cadence — too invasive for this spec.
- **Fixing the upstream cause of bursty emission** in /dev-next (steps 8-9 emit preflight_ok / handoff_read / spec_read back-to-back in the same second). Out of scope; would need per-step delays or restructuring.

## 6. Test plan

- [ ] Test: `tests/spec_lifecycle/test_stages_cycle_started.py` — given fixture events `[{step:cycle_started, ts:T+0}, {step:preflight_ok, ts:T+30}]` and `failure_step=None`, assert pre-flight stage `duration_seconds == 30`. Without fix: returns 0 because `in_progress` (or its absence) anchors elsewhere. With fix: returns 30.
- [ ] Test: `tests/spec_lifecycle/test_stages_anchor_fallback.py` — given events with `queued` but no `cycle_started` or `in_progress`, assert anchor is `queued` and pre-flight duration is computed against it.
- [ ] Test: `tests/spec_lifecycle/test_render_dashboard_meta_refresh.py` — render a fixture spec and assert generated HTML contains `<meta http-equiv="refresh" content="60">` in `<head>`.
- [ ] Test: `tests/spec_lifecycle/test_render_dashboard_data_attrs.py` — render an in-flight fixture (one with `status: in_progress`) and assert the generated HTML contains a `data-cycle-started-at` attribute with an ISO-8601 timestamp value, and a `data-stage-started-at` on the current-stage element.
- [ ] Manual: open the dashboard during a live `/dev-next` cycle; observe ELAPSED counter incrementing every second without reloading.
- [ ] Manual: invoke any /spec-queue, observe browser auto-reloading within 60s and showing the new spec in the queue table.
- [ ] Manual: trigger a dashboard workflow run; confirm green at the deploy step (Path A) or green workflow with no deploy step (Path B).

## 7. Risks

- **Meta-refresh disrupts user interaction.** Mid-scroll readers lose position when the page reloads. Mitigation: 60s is long enough that typical read-then-act cycles complete first; dashboard pages are read-only (no forms to lose). If complaints surface, drop to 90s or 120s in a quick follow-up.
- **Live ticker shows misleading values for stale dashboards.** If the dashboard hasn't redeployed in hours, the ticker correctly increments from `data-stage-started-at` (a real timestamp) using `Date.now()` — so "13 hours elapsed on Branch stage" appears. This is actually *useful diagnostic signal* (something is wrong with the cycle or with the workflow), not a bug. Document in render comment.
- **Deploy-pages Path A requires manual repo settings change.** Mitigation: spec explicitly calls this out, and Path B (remove the deploy job) is the fallback. /dev-next implementer chooses based on what they can verify works.
- **`cycle_started` event in /dev-next adds one more commit-or-buffer step.** Mitigation: emit it but buffer it into the same step-12 commit as the other early events. Zero new commits.
- **Legacy specs with `queued` anchor conflate queue-dwell time with pre-flight execution.** Acceptable — legacy specs are already deployed; their dashboard view is historical. New cycles use `cycle_started` and show real timing.
- **JS asset adds a new file to serve.** Mitigation: ~30 lines, no external dependencies, served from the same Pages origin as the HTML. No CDN concerns.
