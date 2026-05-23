---
kind: dev
spec: "0195"
slug: all-runs-zero-seconds-ago-for-no-transcript-rows
title: "Fix: All-Runs renders `0s ago` for abandoned rows that have no transcript"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 11
depends_on: []
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T11:19:40Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-spec-0181
promoted_from_draft: ""
---

# Spec 0195 — Fix: All-Runs renders `0s ago` for abandoned rows that have no transcript

> **Type:** bug  |  **Severity:** P2  |  **Affects:** All-Runs list (FS-backed `summarize_run` path); the "started" column on rows whose `transcript.jsonl` is empty or missing. Most visible on the four legacy `abandoned` rows surfaced by spec 0181.
> **Bump:** PATCH — display bug, no schema / wire-format / orchestrator change.
> **Evidence:** Spec 0181 implementation handoff — [handoffs/2026-05-23-spec-0181-run-status-staleness-and-abandoned.md:44](handoffs/2026-05-23-spec-0181-run-status-staleness-and-abandoned.md:44). The four user-flagged rows that flipped to `ABANDONED` post-deploy (e.g. `20260515-103340-sample-brief`) render their "started" cell as `0s ago` because their `transcript.jsonl` never had any events for `_earliest_event_ts` to read. The bug pre-dates spec 0181 (those rows used to render `"0s ago running"` — equally misleading) but is now noticeable because the column is highlighted on `abandoned` rows that the user is auditing.

---

## 1. Reproduction

**Environment:** Live deployment of `https://dual-research-alex.fly.dev/` against the production Supabase project — but the bug is specifically in the FS-backed (`summarize_run`) path. Reproducible locally with any session dir whose `transcript.jsonl` is empty or missing.

**Steps:**

1. Create a session directory that mimics a crashed-before-first-event orchestrator. For example: `mkdir -p /tmp/dr-repro/20260101-000000-crashed-run && echo '{"phase": "phase2"}' > /tmp/dr-repro/20260101-000000-crashed-run/state.json` (no `transcript.jsonl`).
2. Point a local server at `/tmp/dr-repro` as a runs root, or call `summarize_run(Path("/tmp/dr-repro/20260101-000000-crashed-run"))` directly.
3. Inspect the returned `RunListRow`: `started_at` is `None` and `started_at_ago` is `0`. The list renders the "started" cell via `fmt.relTime(run.startedAtAgo)` at [src/dual_research/ui/static/run-list.jsx:480](src/dual_research/ui/static/run-list.jsx:480), which returns `"0s ago"` for any input < 60.

**Expected:** Rows with no real start signal render as `"—"` (or `"unknown"`) in the started column. Better — fall back to the parsed session-dir timestamp (the `YYYYMMDD-HHMMSS` prefix) so the row shows its true age (`8d ago` for the user-flagged rows), matching what the staleness signal already does in `_last_activity_ts` at [src/dual_research/ui/aggregator.py:1162-1173](src/dual_research/ui/aggregator.py:1162).

**Actual:** The cell reads `"0s ago"`, implying the run started moments ago — visually contradicting the `ABANDONED` chip on the same row and visually misleading on any row that genuinely is 8 days old. See screenshots of the four rows in the spec 0181 handoff's "Verify" section.

## 2. Root cause hypothesis

`summarize_run` derives `started_at` purely from `_earliest_event_ts(transcript.jsonl)`:

- [src/dual_research/ui/aggregator.py:314](src/dual_research/ui/aggregator.py:314) — `started_at = _earliest_event_ts(session_dir / "transcript.jsonl")`.
- [src/dual_research/ui/aggregator.py:360](src/dual_research/ui/aggregator.py:360) — `started_at_ago=_seconds_since(started_at)`.

`_earliest_event_ts` ([src/dual_research/ui/aggregator.py:1081-1097](src/dual_research/ui/aggregator.py:1081)) returns `None` when the transcript is missing, empty, or has no parseable lines. `_seconds_since` ([src/dual_research/ui/aggregator.py:1177-1184](src/dual_research/ui/aggregator.py:1177)) coerces `None` to `0`. The frontend then renders `0` as `"0s ago"` via `fmt.relTime` at [src/dual_research/ui/static/shared.jsx:665-670](src/dual_research/ui/static/shared.jsx:665) — the `< 60` branch matches `0`.

The staleness signal in `_last_activity_ts` ([src/dual_research/ui/aggregator.py:1134-1174](src/dual_research/ui/aggregator.py:1134)) already solves the underlying "what's the floor timestamp for a run with no transcript" problem: it falls back to `state.json` / `metrics.json` mtime, then to the parsed `YYYYMMDD-HHMMSS` prefix. The `started_at` derivation skipped that fallback ladder because the original assumption (transcript exists once a run starts) was fine for the FS-backed write path until spec 0181 exposed the `abandoned` lifecycle status for rows whose transcript never existed.

## 3. Fix

Two coordinated changes — one server-side fallback, one client-side guard. The client guard alone is not enough because the column would then read `"—"` for every legacy row even when a real timestamp is reconstructible from the dir name. The server fallback alone leaves us with no defence against a future call site that wires up a `started_at` without a sensible floor.

### 3.1 — Server: factor out an `_earliest_known_ts` helper and call it from `summarize_run`

Add a sibling to `_earliest_event_ts` in [src/dual_research/ui/aggregator.py:1081](src/dual_research/ui/aggregator.py:1081):

```python
def _earliest_known_ts(session_dir: Path) -> str | None:
    """Spec 0195 — best-effort 'when did this run start' timestamp.

    Priority (mirrors _last_activity_ts at line 1134 but for the earliest,
    not latest, timestamp):
    1. First event ts in transcript.jsonl (the canonical signal).
    2. Parsed YYYYMMDD-HHMMSS prefix from the session dir name (the
       absolute floor — set at session-dir creation time, before any
       event is emitted).

    A run with neither returns None, and the caller decides how to render
    that (the frontend renders None as `"—"`).
    """
    ts = _earliest_event_ts(session_dir / "transcript.jsonl")
    if ts:
        return ts
    m = _SESSION_DIR_TS_RE.match(session_dir.name)
    if m:
        date_part, time_part = m.groups()
        try:
            return (
                datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S")
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
        except ValueError:
            return None
    return None
```

Wire the new helper into `summarize_run` at [src/dual_research/ui/aggregator.py:314](src/dual_research/ui/aggregator.py:314):

```python
started_at = _earliest_known_ts(session_dir)
```

`_seconds_since(started_at)` at [src/dual_research/ui/aggregator.py:360](src/dual_research/ui/aggregator.py:360) is unchanged — it still returns `0` for the `started_at is None` case, but in practice the new helper supplies the dir-name floor for every realistically-named session dir, so `started_at_ago == 0 AND started_at is None` becomes the genuine "we have no signal at all" path that the frontend guard (§3.2) catches.

The replay path (`load_run_snapshot` at [src/dual_research/ui/aggregator.py:86](src/dual_research/ui/aggregator.py:86)) stays on `_earliest_event_ts` because that path is reading event-driven data and `Run.started_at` is overwritten by the actual `run_started` event when one arrives.

### 3.2 — Client: render `"—"` when both signals are absent

In [src/dual_research/ui/static/run-list.jsx:480](src/dual_research/ui/static/run-list.jsx:480), guard the cell:

```jsx
<span className="mono" style={{ fontSize: 11.5, color: 'var(--md-on-surface-muted)' }}>
  {run.startedAt || run.startedAtAgo > 0 ? fmt.relTime(run.startedAtAgo) : '—'}
</span>
```

Logic: if we have an ISO timestamp OR a non-zero seconds-ago count, render the relative time as today. Only show `"—"` when both signals are missing. The em-dash matches the existing "missing data" convention (search `run-list.jsx` for `'—'` — none today; this introduces the convention for the started column specifically, but matches the dashes used in `fmt.duration` and `fmt.cost` for missing rounds).

### 3.3 — Supabase-backed list path

[src/dual_research/ui/server.py:1050](src/dual_research/ui/server.py:1050) reads `started_at = r.get("created_at")` from the `runs` row. `created_at` is set by the table default on INSERT and is always present for a row that exists — `started_at_ago` is never `0` for that path. No change needed; the bug is FS-only. Adding a defensive `if not started_at:` branch is not warranted given the schema invariant.

### 3.4 — Net diff summary

- **`src/dual_research/ui/aggregator.py`** — new `_earliest_known_ts` helper (~20 LOC); `summarize_run` call site swap (1 LOC).
- **`src/dual_research/ui/static/run-list.jsx`** — one-line guard at the cell renderer.
- **CHANGELOG entry** under `### Fixed` per CLAUDE.md, linking back to this spec.
- **`pyproject.toml` + `src/dual_research/__init__.py`** — PATCH version bump per CLAUDE.md.
- **New test cases:** extend `tests/test_run_status_staleness.py` (adjacent surface area — both helpers live on `aggregator.py` and are exercised through `summarize_run`) OR a new `tests/test_started_at_fallback.py`. Implementer's choice; see §4.

No schema migration. No DS change (we are using an existing token / typography). No two-place CSS sync (the dash glyph is plain text, not a class).

## 4. Regression-prevention test

Two assertions on `summarize_run` cover the server-side fix; one DOM-level assertion (if practical) on the frontend covers the cell guard.

```python
def test_summarize_run_falls_back_to_session_dir_ts_for_started_at(tmp_path: Path):
    """No transcript → started_at parsed from the YYYYMMDD-HHMMSS dir name.

    Locks the spec 0195 fix: rows that never emitted any event still
    report a sensible started_at instead of None → 0s ago.
    """
    from dual_research.ui import aggregator

    session_dir = tmp_path / "20260101-120000-no-transcript"
    session_dir.mkdir()
    (session_dir / "state.json").write_text('{"phase": "phase2"}')

    row = aggregator.summarize_run(session_dir)
    assert row.started_at is not None
    assert row.started_at.startswith("2026-01-01T12:00:00")
    assert row.started_at_ago > 0


def test_summarize_run_returns_none_when_no_ts_signal(tmp_path: Path):
    """Dir name without a YYYYMMDD prefix + no transcript → started_at is None.

    Frontend renders this as "—" rather than "0s ago".
    """
    from dual_research.ui import aggregator

    session_dir = tmp_path / "weird-name-no-ts-prefix"
    session_dir.mkdir()
    (session_dir / "state.json").write_text('{"phase": "phase2"}')

    row = aggregator.summarize_run(session_dir)
    assert row.started_at is None
    assert row.started_at_ago == 0
```

Frontend assertion (optional — only if a vitest-backed run-list test surface exists; today there isn't one for `RunRow`, so this is best skipped):

- [ ] Test: `test_summarize_run_falls_back_to_session_dir_ts_for_started_at` — locks the dir-name fallback path.
- [ ] Test: `test_summarize_run_returns_none_when_no_ts_signal` — locks the "render as dash" path.

**Before-fix behaviour.** Both Python tests fail — current `summarize_run` returns `started_at=None` for the first case (which would also pass the second's first assertion, but `started_at.startswith` errors out on `None`).

**After-fix behaviour.** Both tests pass.

## 5. Blast radius

- **`RunListRow.started_at` semantics.** Today: "ISO ts of the first transcript event, or None". After: "ISO ts of the first transcript event, falling back to the session-dir creation timestamp, or None when neither exists". Strictly broader signal — no consumer of the field expects `None` to mean "started right now"; consumers either render the timestamp or render the relative-seconds count, and both improve when the field carries a real value.
- **`RunListRow.started_at_ago`.** Wire format unchanged. The field becomes a more accurate non-zero value for the previously-zero rows. Any downstream consumer (the sort comparator at [src/dual_research/ui/static/run-list.jsx:31](src/dual_research/ui/static/run-list.jsx:31) keyed on `r.startedAtAgo`) gets better data — rows that previously sorted as "0s ago = newest" stop floating to the top of the started-desc list.
- **Sort order side-effect.** The four user-flagged `abandoned` rows currently sort to the very top of `started:desc` because `0` < everything else under `invert: true`. After the fix they sort to their true age — 8 days old → near the bottom of the recent-first list. The sort comparator at [src/dual_research/ui/static/run-list.jsx:31](src/dual_research/ui/static/run-list.jsx:31) is unchanged; only the input values shift. This is the intended user-facing improvement.
- **`load_run_snapshot` (detail page).** Untouched. The detail page reads `Run.started_at` set by `_on_run_started` at [src/dual_research/ui/aggregator.py:371](src/dual_research/ui/aggregator.py:371) when the `run_started` event fires; the cold-start fallback at [src/dual_research/ui/aggregator.py:86](src/dual_research/ui/aggregator.py:86) still uses `_earliest_event_ts` and that's fine — for a run with no transcript, the detail page already renders empty for nearly every field, and a dash-vs-zero in the "started" header is the least of the user's concerns at that point.
- **Supabase-backed list (`server.py:1050`).** Untouched — `created_at` is always present for a row that exists.
- **No DS change.** No new chip, no new tone, no two-place CSS sync. The dash glyph is rendered as plain text from JSX.

## 6. Out of scope

- **Backfilling the `started_at` column on Supabase-backed runs.** `created_at` is already there and correct.
- **Updating the detail-page "started" header for runs with no transcript.** The detail page has its own rendering convention and is rarely opened for never-started runs; deferring until there's a user complaint.
- **Making `relTime` render `"—"` for `s === 0`.** Tempting one-line fix, but a run that genuinely just started 0 seconds ago should still render as `"0s ago"`. The decision lives at the call site, not in the formatter.
- **Threshold tuning** for what counts as "fresh enough to render". The boolean check `startedAt || startedAtAgo > 0` is sufficient.
- **A second helper for `_latest_known_ts` paralleling `_earliest_known_ts`.** `_last_activity_ts` already plays that role (see [src/dual_research/ui/aggregator.py:1134](src/dual_research/ui/aggregator.py:1134)) — no need to rename or refactor.

## 7. Risks

- **Dir-name parse confusion.** Some session dirs in the wild may have a non-standard prefix (e.g. user-created scratch dirs that don't match `YYYYMMDD-HHMMSS-`). For those, `_SESSION_DIR_TS_RE` doesn't match and the helper returns `None` — frontend then renders `"—"`. Acceptable degradation; matches the existing convention for missing-data cells.
- **Test surface area expansion.** Adding two `summarize_run` tests to a file titled `test_run_status_staleness.py` is mildly off-topic; the implementer may prefer a new `tests/test_started_at_fallback.py`. Either lands in the same PR. No functional impact.
- **`_earliest_known_ts` vs `_last_activity_ts` naming.** Slightly asymmetric (`_known_ts` vs `_activity_ts`). The names match what they describe — earliest known start point vs latest activity moment — but a future refactoring spec may want to unify them under a single fallback ladder. Out of scope here.
- **Session-dir clock skew.** The `YYYYMMDD-HHMMSS` prefix is generated client-side at run start; in theory a host with a clock skewed by hours would seed a wrong floor. In practice the orchestrator runs on Fly machines whose clocks are NTP-synced, and the four user-flagged rows have correct prefixes. Negligible risk.
- **Sort-order regression.** The four currently-stuck-at-top `abandoned` rows fall to their true position in the list after the fix. Users who had been treating "always at top" as the signal for "this is where the abandoned ones live" lose that quirk — but they now have an explicit `abandoned` filter chip (added in spec 0181) for that exact purpose, so the loss is neutral or positive.
