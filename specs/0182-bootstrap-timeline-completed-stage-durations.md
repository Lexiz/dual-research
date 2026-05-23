---
kind: dev
spec: "0182"
slug: bootstrap-timeline-completed-stage-durations
title: "Fix: bootstrap timeline shows `—` for completed-stage durations after `/api/data` refresh"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 10
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T21:45:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0177
promoted_from_draft: ""
---

# Spec 0182 — Fix: bootstrap timeline shows `—` for completed-stage durations after `/api/data` refresh

> **Type:** bug  |  **Severity:** P2  |  **Affects:** spec dashboard in-flight hero timeline, rendered client-side after the 5s `/api/data` repaint.
> **Bump:** PATCH — single-method change to `computeStages` in `DASHBOARD_BOOTSTRAP_JS`.
> **Evidence:** Spec 0177 handoff `## Deferred during implementation` first bullet — [handoffs/2026-05-22-spec-0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md:40](handoffs/2026-05-22-spec-0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md:40).

---

## 1. Reproduction

**Environment:** any browser pointed at `https://lexiz.github.io/dual-research/` or local `uv run python -m scripts.spec_lifecycle.render_dashboard` when the dashboard has one in-flight spec.

**Steps:**

1. Load the dashboard with an in-flight spec — the server-rendered HTML carries the full horizontal stage timeline under the hero, with real per-stage durations (e.g. `1m 12s`) printed in every completed `.tl__dur` cell.
2. Wait ≥ 5 seconds for the bootstrap client's poll of `/api/data` to fire and repaint the page.
3. Inspect any completed `.tl__step--done` node's `.tl__dur` cell after the repaint.

**Expected:** Completed-stage `.tl__dur` cells continue to show the same per-stage duration that the server-rendered first paint showed (e.g. `1m 12s`, `4m 03s`). The current stage's `.tl__dur` keeps ticking live via `data-stage-started-at`.

**Actual:** Every completed stage's `.tl__dur` flips to the literal string `—` (em-dash). Only the current stage's cell remains live and accurate (because `dashboard-live.js`'s 1s ticker keeps rewriting that one node via `data-stage-started-at`). Refreshing the browser tab restores the durations until the next 5s repaint wipes them again.

## 2. Root cause hypothesis

The client-side stage-state computation does not derive per-stage durations. [scripts/spec_lifecycle/render_dashboard.py:3227](scripts/spec_lifecycle/render_dashboard.py:3227) — `computeStages(events, failureStep)` in `DASHBOARD_BOOTSTRAP_JS` resolves only the four state strings (`done` / `curr` / `queued` / `fail`) per stage and returns `{ name, status, ev }`. It never walks event timestamps to compute the elapsed seconds between consecutive stages.

The downstream renderer is then forced to emit `—` for every node's duration cell — see [scripts/spec_lifecycle/render_dashboard.py:3276](scripts/spec_lifecycle/render_dashboard.py:3276) where `renderTimeline` always writes `<div class="tl__dur"…>—</div>` for every step, with the only special-case being the `data-stage-started-at` attribute on `curr`. The server-side renderer at [scripts/spec_lifecycle/stages.py:172](scripts/spec_lifecycle/stages.py:172) (`compute_stages`) does the right thing — it computes `duration_seconds` per stage as the delta between consecutive event timestamps anchored at `cycle_started` / `queued` / `in_progress`. The bootstrap client is missing the equivalent logic.

The reason this slipped past the spec 0177 test surface is that [tests/spec_lifecycle/test_render_dashboard_spec_0177.py](tests/spec_lifecycle/test_render_dashboard_spec_0177.py) asserts `.tl__step` *count* and the *server-rendered* timeline structure but never re-executes the bootstrap's `computeStages` against an `events` array nor inspects `.tl__dur` text content after a simulated repaint.

## 3. Fix

Single-method change to `computeStages` plus a one-line edit to `renderTimeline`. No CSS / DS / Python change.

### 3.1 — Extend `computeStages` to compute per-stage durations

[scripts/spec_lifecycle/render_dashboard.py:3227](scripts/spec_lifecycle/render_dashboard.py:3227). Add a `duration_seconds` field to each returned state, computed as the delta between consecutive event timestamps. Mirror the algorithm in [scripts/spec_lifecycle/stages.py:225-263](scripts/spec_lifecycle/stages.py:225):

- Anchor: pick the first non-null event among `cycle_started`, `queued`, `in_progress` (in that order). Its `ts` is the starting `prev_ts`.
- For each stage `i`, if the stage's event is in `byStep`, set `duration_seconds = max(0, floor((ev.ts - prev_ts) / 1000))` (the JS event objects carry ms-precision ISO strings — `new Date(ts).getTime()` returns ms); then advance `prev_ts` to `ev.ts`.
- For the current stage (`status === 'curr'`), if `prev_ts` is set, `duration_seconds = max(0, floor((Date.now() - prev_ts) / 1000))`. This makes the cell render with a real number on first paint; the per-second ticker via `data-stage-started-at` continues to overwrite it live.
- For queued / fail stages, leave `duration_seconds = null`.

Return shape becomes `{ name, status, ev, duration_seconds }`. The existing `name`, `status`, `ev` keys are unchanged — no caller breaks.

### 3.2 — `renderTimeline` writes the duration into `.tl__dur`

[scripts/spec_lifecycle/render_dashboard.py:3265-3279](scripts/spec_lifecycle/render_dashboard.py:3265). Replace the hard-coded `—` with a small helper that formats `duration_seconds`:

```js
function _fmtDurSecs(secs) {
  if (secs == null) return '—';
  if (secs < 60) return secs + 's';
  var m = Math.floor(secs / 60);
  var s = secs % 60;
  return m + 'm ' + (s < 10 ? '0' : '') + s + 's';
}
```

The format must match what the server-side `_humanize_seconds` would print for stage durations — verify the format in [scripts/spec_lifecycle/render_dashboard.py:802-871](scripts/spec_lifecycle/render_dashboard.py:802) (`_humanize_seconds` and its caller for the Lifetime/Cycle columns) and pick the same shape used for sub-hour stage durations on the server-rendered first paint. Implementation note: the per-stage durations on first paint come from `compute_stages` → `StageState.duration_seconds` rendered through the server's stage-row helper; whatever string that produces is the format `_fmtDurSecs` must match. If the server uses `_humanize_seconds(secs, weeks=False)` and the result is e.g. `"1m 12s"`, mirror that exactly.

The `.tl__step--curr` node continues to get `data-stage-started-at` so the live ticker keeps rewriting the text — but now the initial value is correct instead of `—`.

### 3.3 — Anchor parity with the server-side computation

The anchor preference order in §3.1 (`cycle_started` → `queued` → `in_progress`) matters: it must exactly mirror [scripts/spec_lifecycle/stages.py:225-229](scripts/spec_lifecycle/stages.py:225) so that pre-flight gets a real duration on historical specs that pre-date `cycle_started`. The bootstrap's `events` array is the same data the server uses (both come from `dashboard/events/NNNN.jsonl` via `/api/data`), so the anchor lookup is a direct port.

## 4. Regression-prevention test

New test inside [tests/spec_lifecycle/test_render_dashboard_spec_0177.py](tests/spec_lifecycle/test_render_dashboard_spec_0177.py) (or a sibling file `test_render_dashboard_spec_0182.py` if the implementer prefers). The test renders the dashboard, then extracts the inline `DASHBOARD_BOOTSTRAP_JS` block, executes the `computeStages` JS function against a synthetic events array via the `js2py` or `pythonmonkey` runtime — *or* asserts the new fields are present by source-substring matching.

The minimally-coupled form (no JS runtime needed):

- [ ] Test: `test_bootstrap_compute_stages_returns_duration_seconds` — searches the inline JS source for the new `duration_seconds` field on the object returned by `computeStages`. Fails before the fix because the literal string `duration_seconds` does not appear in `DASHBOARD_BOOTSTRAP_JS`; passes after.
- [ ] Test: `test_bootstrap_render_timeline_uses_fmt_dur_secs` — searches for the new `_fmtDurSecs` helper invocation inside `renderTimeline`. Locks the fix point so that a future refactor that drops the helper while keeping the field would still flag.

A heavier integration test using `js2py` against `computeStages` directly with a synthetic events array would be the gold standard; defer that to the implementer if the test harness already has a JS runtime hookup. Otherwise the two source-substring tests are sufficient — the fix is local enough that lexical evidence is reliable.

## 5. Blast radius

- **Files touched.** [scripts/spec_lifecycle/render_dashboard.py:3227-3279](scripts/spec_lifecycle/render_dashboard.py:3227) only. Two functions inside the embedded `DASHBOARD_BOOTSTRAP_JS` constant — `computeStages` and `renderTimeline` — plus the new `_fmtDurSecs` helper.
- **Consumers of `computeStages`.** Sole caller is `renderHeroInflight` at [scripts/spec_lifecycle/render_dashboard.py:3361](scripts/spec_lifecycle/render_dashboard.py:3361) (verified via grep of the JS source block). Adding a field is backward-compatible — the caller already reads only `{ name, status, ev }` and ignores any extra keys.
- **`data-stage-started-at` ticker.** The 1s ticker that rewrites the current-stage cell (referenced in the renderTimeline comment at [scripts/spec_lifecycle/render_dashboard.py:3267](scripts/spec_lifecycle/render_dashboard.py:3267)) keeps working unchanged — it overwrites the `.tl__dur` `textContent` regardless of the initial value.
- **No DS change.** No new CSS classes, no token changes, no `composed-components.css` / `components.css` edits. The DS-sync rule does not apply.
- **No backend change.** The `events` array shape carried by `/api/data` is unchanged.

## 6. Out of scope

- Equivalent fix for any *other* JS-side stage computation. There is only one (the bootstrap's `computeStages`); the rest are server-side Python (`stages.compute_stages`).
- Refactoring the duration format to a shared helper between server and client. The server uses `_humanize_seconds`; the client gets its own `_fmtDurSecs`. Cross-language helper sharing is overkill for two callers.
- Pixel-level fidelity check against the mockup — that's spec 0184's job (per the spec 0177 handoff deferral list).

## 7. Risks

- **Format drift.** If `_fmtDurSecs` and the server's stage-duration formatter disagree on edge cases (e.g. `0s` vs `—`, or seconds vs minutes threshold), the timeline will flicker between the two formats on each repaint. Mitigation: implementer picks the server's output as the spec for `_fmtDurSecs` and locks it with a unit test that diffs the two helpers' outputs for the same input set.
- **Anchor mismatch on legacy specs.** Specs that pre-date the `cycle_started` event would, before this fix, render `—` for the pre-flight stage on first paint too (the server falls back to `queued` then `in_progress`). The client must use the same fallback chain so first paint and repaint agree. Risk is small — the fallback chain is explicit in the spec.
- **Date parsing.** JS `new Date(iso).getTime()` returns NaN for malformed ISO strings. Guard with `if (!isFinite(ms))` and fall back to leaving `duration_seconds = null` rather than emitting NaN. The events on disk are well-formed (written by `append_event.py`) but defensive coding here costs one line.
