---
kind: dev
spec: "0181"
slug: run-status-staleness-and-abandoned
title: "Fix: All-Runs reports `running` for runs that died days ago — add time-based liveness check + new `abandoned` lifecycle status"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 3
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T23:25:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: bug-spec-batch-2205-claude
promoted_from_draft: ""
---

# Spec 0181 — Fix: All-Runs reports `running` for runs that died days ago

> **Type:** bug  |  **Severity:** P1  |  **Affects:** every run-status surface that reads the unified truth table — All-Runs list (FS-backed `summarize_run` + Supabase-backed `_status_from_columns`) and the run-detail page (`_finalise_status` after every event replay). Live since spec 0136 unified the truth table without time-based liveness.
> **Bump:** PATCH — bug fix; one new status enum value (`abandoned`) and one new threshold constant. No schema change (the wire format already carries the timestamps required). No backend-orchestrator change.
> **Evidence:** Notion bug-batch page "Specs 2205 (Claude)" Bug 6 (`https://www.notion.so/Specs-2205-Claude-36899f3e507f802a90f6df0566d9704b`). User report: "there are currently in the database four runs that are marked as running but none of them are actually running. These are very old runs. Ranging between two and six days ago." Spec 0136 consolidated three divergent status derivers onto one truth table but the table's terminal fallback ([labels.py:172](src/dual_research/ui/labels.py:172) — `return "running"`) treats "no terminal event observed" as `running` indefinitely. There is no reaper or liveness check.

---

## 1. Reproduction

**Environment.** Live deployment of `https://dual-research-alex.fly.dev` against the production Supabase project. Any run whose orchestrator process crashed / was killed / had its host recycled before emitting `run_completed` or `run_failed` to the transcript — exactly four such rows are present in the production database right now per the user's report (created 2-6 days ago, all stuck at `running`).

**Steps.**

1. Inspect the Supabase `runs` table. Identify rows where `exit_code IS NULL`, `phase_reached != 'done'`, `state->>'final_emitted_to' IS NULL`, and `created_at < now() - interval '1 hour'`. These are the candidate rows for the bug.
2. Open the All-Runs list (`/api/runs` or the dashboard view that consumes it). Read each candidate row's `status` field.

**Expected:** A row whose orchestrator hasn't emitted any event in the last 30 minutes and never recorded a terminal signal should report `abandoned` (new status), not `running`. The lifecycle policy is data-driven (timestamp + state, not hard-coded id lists) and applies uniformly across the FS-backed list scan, the Supabase-backed list scan, and the detail-page replay.

**Actual:** Every such row reports `status: "running"`. The four user-flagged rows have been reporting `running` for between 2 and 6 days. The All-Runs list and the per-run detail view sometimes disagree on the same row — most commonly the detail page shows the last applied event's phase while the list shows a different phase string snapshot — but they agree on `status: "running"` because both consult the same `derive_run_status` fall-through at [labels.py:172](src/dual_research/ui/labels.py:172).

3. Open the detail page for one of the candidate rows. The page renders with `Run.status === "running"` and displays the running-state chrome (live activity dot, pulse animation, "in progress" copy) even though no event has arrived in days.

**Expected:** Detail page agrees with the list — `abandoned`. UI surfaces the same chip / tone / copy across both views.

**Actual:** Detail page renders `running` chrome indefinitely.

The Notion report frames the symptom with the user's exact words: *"the governance of the logic of how to show life cycle statuses just doesn't seem to be correct. I hope it's not like some hard-coded bullshit."* — i.e. the user is asking for a real time-based lifecycle policy, not another localised patch.

## 2. Root cause hypothesis

Spec 0136 unified three divergent status derivers (orchestrator exit-code emission, All-Runs list scan, run-detail replay) onto a single truth table at [src/dual_research/ui/labels.py:113-172](src/dual_research/ui/labels.py:113). The table's six precedence rules cover terminal signals (`run_failed`, non-zero exit code, hard cap, `final_emitted`, clean exit) but the fall-through at [labels.py:172](src/dual_research/ui/labels.py:172) — `return "running"` — has no time bound. Any row where no terminal signal was ever recorded reports `running` until a terminal event arrives. For a run whose process died before writing any terminal event, that's forever.

The Supabase-backed path encodes the assumption explicitly. [src/dual_research/ui/server.py:1075-1100](src/dual_research/ui/server.py:1075) `_status_from_columns` carries a docstring (line 1078) reading: *"Pushed runs are by definition completed (push happens post-run), so we only really see done / errored / deadlocked here."* That assumption is false for two reasons:

- **Mid-flight pushes exist.** Spec 0032's `--push-while-running` writes Supabase rows during the run (the row exists before the terminal events do). The docstring's "push happens post-run" invariant predates that mode.
- **Partial pushes followed by a crash.** A run that pushed once mid-flight then crashed leaves the row with `exit_code IS NULL`, `state.final_emitted_to` unset, `phase_reached` at whatever the last write captured. The truth table's silent-exit defence branch (line 170 — `exit_code == 0` + not done → `deadlocked`) doesn't fire because `exit_code` is `None`, not `0`.

Concrete code anchors and call sites:

- **Unified truth table.** [src/dual_research/ui/labels.py:113-172](src/dual_research/ui/labels.py:113) (`derive_run_status`). Six precedence rules; the fall-through at line 172 is the gap.
- **FS-backed list scan.** [src/dual_research/ui/aggregator.py:296-323](src/dual_research/ui/aggregator.py:296) (`summarize_run`) reads `state.json` + `transcript.jsonl` and feeds the truth table. The terminal-signals scan is at [src/dual_research/ui/aggregator.py:1202](src/dual_research/ui/aggregator.py:1202) (`_scan_terminal_signals`). Only sees events the transcript actually persisted before the process died.
- **Supabase-backed list scan.** [src/dual_research/ui/server.py:1075-1100](src/dual_research/ui/server.py:1075) (`_status_from_columns`). Reads `phase_reached`, `exit_code`, `state` columns. The docstring at line 1078 is the false invariant.
- **Detail-page replay.** [src/dual_research/ui/aggregator.py:953-980](src/dual_research/ui/aggregator.py:953) (`_finalise_status`). Called after every applied event. Gives up when the event stream stops.
- **Schema.** [supabase/migrations/0001_initial.sql:14-29](supabase/migrations/0001_initial.sql:14) — `runs` carries `created_at`, `pushed_at`, `phase_reached`, `exit_code`, `state` (JSONB). The `events` table at [supabase/migrations/0001_initial.sql:33-40](supabase/migrations/0001_initial.sql:33) carries per-event `ts` (TIMESTAMPTZ). The `events.ts` MAX is the canonical "last activity" timestamp for Supabase-backed runs. The FS-backed equivalent is the last event-ts inside `transcript.jsonl`.
- **Status enum.** [src/dual_research/ui/models.py:21-28](src/dual_research/ui/models.py:21) — `RunStatus = Literal["running", "converged", "deadlocked", "errored", "completed", "idle"]`. The new `"abandoned"` value lands here.

The truth table treating "no terminal event" as `running` is **correct in the absence of a liveness signal**. The fix is to supply that signal: a `last_event_at` parameter to `derive_run_status` and a per-call-site computation feeding it.

## 3. Fix

Extend the truth table with a time-based fallback at the bottom of the precedence list. Plumb a single new timestamp through the three call sites. Add one new status enum value plus its UI badge mapping. No schema change.

### 3.1 — `derive_run_status` gains `last_event_at` + `now` parameters

[src/dual_research/ui/labels.py:113-172](src/dual_research/ui/labels.py:113). New signature:

```python
RUN_STALE_THRESHOLD_MINUTES = 30  # configurable via module constant; not env-driven for now

def derive_run_status(
    *,
    state_phase: str,
    final_emitted: bool,
    hard_cap_hit: bool,
    run_failed: bool,
    run_completed_exit_code: int | None = None,
    last_event_at: str | None = None,
    now: datetime | None = None,
) -> str:
    ...
```

The new precedence becomes:

1. `run_failed` → `errored` (unchanged).
2. Non-zero exit code that isn't 51 → `errored` (unchanged).
3. `hard_cap_hit` or `exit_code == 51` → `deadlocked` (unchanged).
4. `final_emitted` or `state_phase == "done"` → `completed` (unchanged).
5. `exit_code == 0` and not done → `deadlocked` (unchanged — silent-exit defence).
6. **NEW:** `last_event_at` provided AND `(now - last_event_at) > RUN_STALE_THRESHOLD_MINUTES` AND `state_phase != "done"` AND no terminal exit code → `abandoned`.
7. else → `running` (unchanged).

`last_event_at` accepts an ISO-8601 string (timezone-aware preferred — the wire format already carries `Z` suffix). `None` skips the liveness check entirely — preserves backward compatibility for any caller that hasn't been updated. `now` defaults to `datetime.now(timezone.utc)` if not provided — explicit parameter so tests can pin it.

Update the docstring to describe rule 6. Rule numbering shifts in the docstring (old rule 6 → new rule 7).

### 3.2 — `RunStatus` enum gains `"abandoned"`

[src/dual_research/ui/models.py:21-28](src/dual_research/ui/models.py:21). Add `"abandoned"` to the Literal:

```python
RunStatus = Literal[
    "running",
    "converged",
    "deadlocked",
    "errored",
    "completed",
    "idle",
    "abandoned",   # spec 0181 — orchestrator stopped emitting events
                   # for ≥ RUN_STALE_THRESHOLD_MINUTES with no terminal signal
]
```

Type-hint fan-out: search `src/` for any other `Literal[...]` carrying the four-status set — none exist beyond `RunStatus` itself (verified). Any consumer that imports `RunStatus` picks up the new value automatically.

### 3.3 — FS-backed list scan plumbs `last_event_at`

[src/dual_research/ui/aggregator.py:296-323](src/dual_research/ui/aggregator.py:296) (`summarize_run`). Add a helper alongside the existing `_earliest_event_ts`:

```python
def _latest_event_ts(transcript_path: Path) -> str | None:
    """Return the ``ts`` of the last event in the transcript, or None
    if the file is missing / empty. Reads from the end of the file —
    cheap even on long transcripts."""
    if not transcript_path.exists():
        return None
    # Read the last ~64KB to find the final newline-terminated event.
    # Transcripts are JSONL; the last non-empty line is the latest event.
    try:
        with transcript_path.open("rb") as f:
            f.seek(0, 2)  # end
            size = f.tell()
            tail = b""
            chunk = 64 * 1024
            while size > 0 and tail.count(b"\n") < 2:
                read_n = min(chunk, size)
                f.seek(size - read_n)
                tail = f.read(read_n) + tail
                size -= read_n
            last_line = tail.strip().splitlines()[-1] if tail.strip() else b""
            if not last_line:
                return None
            evt = json.loads(last_line)
            return evt.get("ts")
    except (OSError, ValueError, json.JSONDecodeError):
        return None
```

Call site (extending the existing `summarize_run` body):

```python
status = derive_run_status(
    state_phase=state.phase if state else "phase0",
    final_emitted=final_emitted,
    hard_cap_hit=hard_cap_hit,
    run_failed=run_failed,
    run_completed_exit_code=run_completed_exit_code,
    last_event_at=_latest_event_ts(session_dir / "transcript.jsonl"),
)
```

`now=` is omitted at the call site so `derive_run_status` defaults to `datetime.now(timezone.utc)`.

### 3.4 — Supabase-backed list scan plumbs `last_event_at`

[src/dual_research/ui/server.py:1010-1100](src/dual_research/ui/server.py:1010). The current query at line 1020 reads only `runs.*` columns. Two implementation options for the extra `last_event_at` signal:

**Option A — Single JOIN query.** Replace the current `runs` table query with a joined query that pulls each run's `MAX(events.ts)`:

```python
res = (
    client.table("runs")
    .select(
        "id,slug,created_at,pushed_at,phase_reached,exit_code,"
        "duration_ms,total_cost_usd,confidence,state,"
        "events:events(ts)"   # supabase-py join; verify exact syntax
    )
    .order("created_at", desc=True)
    .execute()
)
```

The joined `events.ts` array is processed in Python to extract the MAX. Risk: supabase-py's join syntax may not support aggregation directly — the joined rows might come back as a list per run, requiring a per-run reduce.

**Option B — Two queries.** Keep the existing `runs` query untouched. After fetching N rows, run a single `events` aggregation query: `SELECT run_id, MAX(ts) AS last_ts FROM events WHERE run_id IN (...) GROUP BY run_id` (or the supabase-py equivalent), then join the maps in Python.

**Option C — Use `pushed_at` as a proxy.** The `runs.pushed_at` column exists ([supabase/migrations/0001_initial.sql:18](supabase/migrations/0001_initial.sql:18)) but currently is only set by the table default on INSERT — it does NOT update on UPSERT because `_build_run_row` at [src/dual_research/persistence/remote.py:232](src/dual_research/persistence/remote.py:232) doesn't include `pushed_at` in the returned dict. To make `pushed_at` a usable signal: add `"pushed_at": datetime.now(timezone.utc).isoformat()` to `_build_run_row`'s output so every upsert refreshes it. Then read `pushed_at` directly in `_status_from_columns` — one extra column on the existing query, no JOIN.

**Recommendation: Option C** — smallest blast radius, no query-shape change, no per-row reduce. The "last activity" signal for Supabase-backed runs becomes "last orchestrator push", which is a slightly weaker signal than "last event" (events arrive between pushes too) but for the 30-minute staleness threshold the difference is negligible. The orchestrator's `--push-while-running` cadence is sub-minute, so a run that's been silent for 30+ minutes has either crashed or completed.

Updated `_status_from_columns` signature:

```python
def _status_from_columns(
    *, phase_reached: str, exit_code: int | None, state: dict,
    last_event_at: str | None = None,
) -> str:
    final_emitted = bool(state.get("final_emitted_to"))
    return derive_run_status(
        state_phase=phase_reached,
        final_emitted=final_emitted,
        hard_cap_hit=exit_code == 51,
        run_failed=False,
        run_completed_exit_code=exit_code,
        last_event_at=last_event_at,
    )
```

Updated docstring drops the false invariant ("Pushed runs are by definition completed") and replaces it with: *"Pushed runs may be in-flight (since spec 0032's `--push-while-running`); the `last_event_at` parameter (typically the row's `pushed_at`) drives the staleness check inside `derive_run_status`."*

Call site at line 1053 passes `last_event_at=r.get("pushed_at")`.

`_build_run_row` at [src/dual_research/persistence/remote.py:182](src/dual_research/persistence/remote.py:182) gains one line: `"pushed_at": datetime.now(timezone.utc).isoformat()` inside the returned dict. The column already exists in the schema; we're just refreshing it on every upsert (was relying on `DEFAULT now()` which only fires on INSERT).

### 3.5 — Detail-page replay plumbs `last_event_at`

[src/dual_research/ui/aggregator.py:953-980](src/dual_research/ui/aggregator.py:953) (`_finalise_status`). The function operates on a `Run` dataclass populated by the event replay. Stash the latest event ts during the replay loop:

- Find the event-application loop (search for `apply_event` calls inside `load_run_snapshot` — likely above the `_finalise_status(run)` call at line 292). Each event carries a `ts`. The last applied event's `ts` is the canonical `last_event_at` for the detail-page path.
- Stash it on `run._terminal_signals` (or a sibling field on `Run`): `run._last_event_at: str | None = None` set during replay.
- `_finalise_status` reads `run._last_event_at` and passes it to `derive_run_status`:

```python
run.status = derive_run_status(
    state_phase=state_phase,
    final_emitted=final_emitted,
    hard_cap_hit=sigs.hard_cap_hit,
    run_failed=sigs.run_failed,
    run_completed_exit_code=sigs.run_completed_exit_code,
    last_event_at=getattr(run, "_last_event_at", None),
)
```

If the snapshot was hydrated without a transcript (cold start), `_last_event_at` stays `None` and the liveness check is skipped — `derive_run_status` returns the current behaviour for that path. Existing tests that don't supply a `last_event_at` continue to pass.

### 3.6 — UI badge for `abandoned`

[src/dual_research/ui/static/shared.jsx](src/dual_research/ui/static/shared.jsx). Find the `StatusBadge` component (search for `StatusBadge` in `shared.jsx`). Extend the status → tone / label / icon mapping to cover `"abandoned"`:

- Tone: `warn` (amber). Distinct from `errored` (red) — abandoned means "we don't know what happened", not "we know it failed".
- Label: `Abandoned`.
- Icon: a question-mark or warning glyph from the existing icon set (verify against the icon registry in shared.jsx).
- Tooltip on hover: *"Run stopped emitting events for over 30 minutes with no terminal signal. The orchestrator process likely crashed or was killed before writing a terminal event."*

CSS: if the existing tone tokens cover amber/warn (they should, per `design-system/SPEC.md` §3 chip tones), no new CSS is needed. If not, add `.status-badge--abandoned` to both `src/dual_research/ui/static/components.css` and `design-system/assets/styles/composed-components.css` (the two-place rule from CLAUDE.md).

### 3.7 — Codify the policy in `design-system/SPEC.md` and CHANGELOG

Add a sub-section under §3 (Primitives → StatusBadge) or §9 (Vocabulary) — implementer's choice based on which fits the surrounding text best — codifying:

> **`abandoned` lifecycle status.** A run with `last_event_at < now - 30 min` and no terminal signal (`run_completed`, `run_failed`, hard-cap exit) reports as `abandoned` across the All-Runs list, the run-detail page, and any other surface that consumes `RunStatus`. The threshold lives at `dual_research.ui.labels.RUN_STALE_THRESHOLD_MINUTES`. The policy is data-driven (timestamps + state, not hard-coded id lists). Stale runs already in the database flip to `abandoned` the moment the new derivation logic ships — no migration / backfill required because the truth table is derived live on every read.

CHANGELOG entry under `### Changed`:

```markdown
- All-Runs list and run-detail page now classify silent runs as `abandoned` instead of `running` once they've gone ≥ 30 minutes without an event. New `RunStatus` value (`abandoned`) — `errored` continues to mean "explicit failure with a known cause"; `abandoned` means "orchestrator stopped emitting before writing a terminal event". [spec 0181](specs/0181-run-status-staleness-and-abandoned.md)
```

### 3.8 — Net diff summary

- **`src/dual_research/ui/labels.py`** — `derive_run_status` signature + rule 6 + `RUN_STALE_THRESHOLD_MINUTES` constant. ~30 LOC added.
- **`src/dual_research/ui/models.py`** — `"abandoned"` added to `RunStatus` Literal. 1 LOC.
- **`src/dual_research/ui/aggregator.py`** — new `_latest_event_ts` helper, `summarize_run` + `_finalise_status` updated to pass `last_event_at`. ~40 LOC.
- **`src/dual_research/ui/server.py`** — `_status_from_columns` signature + call site at line 1053. Docstring rewrite. ~10 LOC.
- **`src/dual_research/persistence/remote.py`** — `_build_run_row` gains `pushed_at` refresh. 1 LOC.
- **`src/dual_research/ui/static/shared.jsx`** — StatusBadge gains `abandoned` tone/label/icon mapping. ~10 LOC.
- **`design-system/SPEC.md`** — sub-section added. ~10 lines of prose.
- **`design-system/assets/styles/composed-components.css`** — if any new `.status-badge--abandoned` class is needed (depends on existing tone coverage). Mirror in `src/dual_research/ui/static/components.css`.
- **`CHANGELOG.md`** — one `### Changed` bullet under the version section per CLAUDE.md's per-spec release convention.
- **`pyproject.toml` + `src/dual_research/__init__.py`** — PATCH version bump per CLAUDE.md.
- **New test file:** `tests/test_run_status_staleness.py` — see §4.

No schema migration. No backfill SQL. The truth table is derived live on every read, so stale rows flip the moment the new code ships.

## 4. Regression-prevention test

Two test surfaces — one for the truth table itself (Python unit tests, deterministic with pinned `now`), one for the call-site plumbing (asserting each of the three sites passes `last_event_at`). New file `tests/test_run_status_staleness.py`:

```python
"""Spec 0181 — staleness branch in derive_run_status + call-site plumbing.

The truth table now classifies silent runs as `abandoned`. This test
locks the branch with pinned-now determinism and asserts all three call
sites pass `last_event_at` through to the truth table.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from dual_research.ui.labels import (
    RUN_STALE_THRESHOLD_MINUTES,
    derive_run_status,
)


NOW = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)


def _ts(minutes_ago: int) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


# ─── Truth-table branch ───────────────────────────────────────────────────


def test_silent_run_past_threshold_is_abandoned():
    # No terminal signal, last event > threshold ago → abandoned.
    status = derive_run_status(
        state_phase="phase2",
        final_emitted=False,
        hard_cap_hit=False,
        run_failed=False,
        run_completed_exit_code=None,
        last_event_at=_ts(RUN_STALE_THRESHOLD_MINUTES + 5),
        now=NOW,
    )
    assert status == "abandoned"


def test_silent_run_within_threshold_is_running():
    # No terminal signal, last event recent → running (existing behaviour).
    status = derive_run_status(
        state_phase="phase2",
        final_emitted=False,
        hard_cap_hit=False,
        run_failed=False,
        run_completed_exit_code=None,
        last_event_at=_ts(RUN_STALE_THRESHOLD_MINUTES - 5),
        now=NOW,
    )
    assert status == "running"


def test_silent_run_no_last_event_at_falls_through_to_running():
    # last_event_at=None → backwards-compatible: rule 6 skipped, rule 7 (running) fires.
    status = derive_run_status(
        state_phase="phase2",
        final_emitted=False,
        hard_cap_hit=False,
        run_failed=False,
        run_completed_exit_code=None,
        last_event_at=None,
        now=NOW,
    )
    assert status == "running"


def test_completed_run_ignores_staleness():
    # Terminal signal present — staleness check never fires.
    status = derive_run_status(
        state_phase="done",
        final_emitted=True,
        hard_cap_hit=False,
        run_failed=False,
        run_completed_exit_code=0,
        last_event_at=_ts(60 * 24 * 7),  # week-old
        now=NOW,
    )
    assert status == "completed"


def test_errored_run_ignores_staleness():
    status = derive_run_status(
        state_phase="phase2",
        final_emitted=False,
        hard_cap_hit=False,
        run_failed=True,
        run_completed_exit_code=None,
        last_event_at=_ts(60 * 24 * 7),
        now=NOW,
    )
    assert status == "errored"


def test_deadlocked_run_ignores_staleness():
    status = derive_run_status(
        state_phase="phase2",
        final_emitted=False,
        hard_cap_hit=True,
        run_failed=False,
        run_completed_exit_code=51,
        last_event_at=_ts(60 * 24 * 7),
        now=NOW,
    )
    assert status == "deadlocked"


def test_stale_run_reached_done_is_completed_not_abandoned():
    # Edge: state_phase == "done" but no run_completed event — final_emitted
    # OR state_phase=="done" triggers the completed branch BEFORE the
    # staleness check fires. (Rule 4 wins over rule 6.)
    status = derive_run_status(
        state_phase="done",
        final_emitted=False,
        hard_cap_hit=False,
        run_failed=False,
        run_completed_exit_code=None,
        last_event_at=_ts(60 * 24),
        now=NOW,
    )
    assert status == "completed"


# ─── Call-site plumbing ───────────────────────────────────────────────────


def test_summarize_run_passes_last_event_at(tmp_path: Path):
    """`summarize_run` must read the last event ts from the transcript
    and pass it through to `derive_run_status`."""
    from dual_research.ui import aggregator

    session_dir = tmp_path / "20260101-000000-test-stale"
    session_dir.mkdir()
    # Write a transcript with a single old event.
    transcript = session_dir / "transcript.jsonl"
    transcript.write_text(
        '{"seq": 1, "ts": "2026-01-01T00:00:00+00:00", "kind": "run_started", "payload": {}}\n'
    )
    (session_dir / "state.json").write_text('{"phase": "phase2"}')

    row = aggregator.summarize_run(session_dir)
    # Last event is months old → abandoned.
    assert row.status == "abandoned", (
        f"summarize_run must pass last_event_at to derive_run_status; "
        f"got status={row.status!r}"
    )


def test_status_from_columns_passes_last_event_at():
    """`_status_from_columns` must accept `last_event_at` and pass it through."""
    from dual_research.ui.server import _status_from_columns

    # Old pushed_at → abandoned.
    status = _status_from_columns(
        phase_reached="phase2",
        exit_code=None,
        state={},
        last_event_at="2026-01-01T00:00:00+00:00",
    )
    assert status == "abandoned"

    # Recent pushed_at → running.
    recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    status = _status_from_columns(
        phase_reached="phase2",
        exit_code=None,
        state={},
        last_event_at=recent,
    )
    assert status == "running"
```

**Before-fix behaviour.** The truth-table tests fail (current `derive_run_status` doesn't accept `last_event_at` or `now`). The two call-site tests fail (`summarize_run` and `_status_from_columns` don't compute / pass the signal).

**After-fix behaviour.** All nine tests pass.

- [ ] Test: `test_silent_run_past_threshold_is_abandoned` — locks the new branch.
- [ ] Test: `test_silent_run_within_threshold_is_running` — locks the threshold semantics.
- [ ] Test: `test_silent_run_no_last_event_at_falls_through_to_running` — locks backward compatibility.
- [ ] Test: `test_completed_run_ignores_staleness` — locks rule 4 precedence over rule 6.
- [ ] Test: `test_errored_run_ignores_staleness` — locks rule 1 precedence.
- [ ] Test: `test_deadlocked_run_ignores_staleness` — locks rule 3 precedence.
- [ ] Test: `test_stale_run_reached_done_is_completed_not_abandoned` — edge case where state_phase=="done" but no run_completed event.
- [ ] Test: `test_summarize_run_passes_last_event_at` — locks FS-side plumbing.
- [ ] Test: `test_status_from_columns_passes_last_event_at` — locks Supabase-side plumbing.

A detail-page-replay equivalent test (`test_finalise_status_passes_last_event_at`) is recommended but requires constructing a full `Run` dataclass with `_terminal_signals` and `_last_event_at` set — defer to implementation if the test surface for `_finalise_status` already exists; otherwise the unit-level coverage of `derive_run_status` is sufficient because `_finalise_status` is a thin pass-through.

## 5. Blast radius

- **Files touched.** `src/dual_research/ui/labels.py`, `src/dual_research/ui/models.py`, `src/dual_research/ui/aggregator.py`, `src/dual_research/ui/server.py`, `src/dual_research/persistence/remote.py`, `src/dual_research/ui/static/shared.jsx`, `design-system/SPEC.md`, `CHANGELOG.md`, `pyproject.toml`, `src/dual_research/__init__.py`, plus a new test file. Optionally `src/dual_research/ui/static/components.css` and `design-system/assets/styles/composed-components.css` if the existing tone tokens don't cover the abandoned badge.
- **Consumers of `derive_run_status`.** Three call sites in `src/`: `summarize_run`, `_status_from_columns`, `_finalise_status`. All three updated under §3.3, §3.4, §3.5 respectively. No other caller (verified via grep).
- **Consumers of `RunStatus`.** The Literal lives in `models.py` and is consumed by `RunListRow.status`, `Run.status`, and the JSON serialiser `to_jsonable`. Adding a new enum value is backward-compatible — existing values continue to validate; any switch statement that doesn't have a case for `"abandoned"` will hit its default branch (which for most UI surfaces is "treat as unknown — render with a neutral tone"). The StatusBadge update at §3.6 is the only consumer that needs an explicit case.
- **`pushed_at` write semantics change.** §3.4 makes `_build_run_row` write `pushed_at` on every upsert. Previously it was set only on INSERT (table default). The change is monotonic — older rows that already have an old `pushed_at` will get their `pushed_at` refreshed on the next push (which is also when their `last_event_at` becomes load-bearing). No backfill needed.
- **No backfill, no migration, no DB writes.** The truth table is derived live on every read. The four user-flagged stale rows flip to `abandoned` the moment the deploy lands. No special handling for the existing four rows.
- **No SSE / event-stream change.** The orchestrator continues to emit events as before. The status derivation runs on the read side only.
- **Wire format unchanged.** `RunListRow.status` carries one more possible string value. JSON consumers that whitelist the four old values will reject `"abandoned"` — there is no JSON consumer outside the dashboard, and the dashboard renderer reads the field as a free string (verified via grep of `dashboard/`).
- **Threshold tunability.** `RUN_STALE_THRESHOLD_MINUTES = 30` lives as a module constant. Not env-driven for this spec — the 30-minute default is a defensible "longest legitimate idle gap inside a healthy run" per the Notion bug. Making it env-driven is a follow-up if operationally needed.

## 6. Out of scope

- **A reaper / janitor process** that actively re-derives stale runs and writes their state back to Supabase. Not needed — the truth table is derived live; live reads return the correct status without any DB write. A janitor would be useful for emitting alerting / metrics off the `abandoned` event, but that's a separate observability concern.
- **Backfill SQL** for the four currently-stale rows. The Notion bug's "verification step 1" instructs the implementer to inspect Supabase for `exit_code IS NULL` rows and count them — that's the *audit* step, not a *write* step. The fix is purely on the read side.
- **Configurable threshold per environment.** 30 minutes is the default; not env-driven for this spec.
- **A different status enum value for "host recycled vs process crashed vs killed by SIGTERM".** All three present identically (silent transcript). The UI can't distinguish; one bucket (`abandoned`) is enough.
- **Alerting / notifications when a run flips to `abandoned`.** Out of scope.
- **Bug 1** (Agent Input split-pane) — spec 0171.
- **Bug 2** (critique-card ID chip + `**`) — spec 0172.
- **Bug 3** (three-section input panel one-click reveal) — spec 0178.
- **Bug 4** (critique-card body redundancies + parity verification) — spec 0179.
- **Bug 5** (Consumption card V2 anatomy) — spec 0180.
- **The `state.phase == "done"` rare-edge from `test_stale_run_reached_done_is_completed_not_abandoned`.** That branch already wins over rule 6 because rule 4 (`final_emitted OR state_phase == "done"`) sits earlier in the precedence. The test locks that precedence.

## 7. Risks

- **False positives — a healthy run that happens to have a 30+ minute API delay.** The orchestrator's `--push-while-running` cadence is well under 30 minutes; a single API call to Claude Opus 4 occasionally takes 5-10 minutes when extended thinking is enabled, but never 30+. If the 30-minute threshold turns out to be too aggressive in practice, raise `RUN_STALE_THRESHOLD_MINUTES` — one-line change. Verification step: after deploy, monitor for any in-flight run that flips to `abandoned` then back to `running`; that's the false-positive signature.
- **`pushed_at` semantics change is a behaviour change masquerading as a bugfix.** Previously `pushed_at` was "first-pushed-at"; now it's "last-pushed-at". Any external consumer of the column reading "first push timestamp" will see a different value. Verification: grep `src/` and `dashboard/` for `pushed_at` references — none today (verified). External consumers (if any exist in user scripts) should be flagged in the deploy notes.
- **JSON consumers that whitelist the four old status values.** A strict-schema consumer (Pydantic v2 with `extra="forbid"`, JSON Schema validator) rejecting `"abandoned"` would error. Mitigation: grep `src/` and `tests/` for `Literal["running"` patterns — only `RunStatus` itself has the whitelist. No external schema validator gates the dashboard payload.
- **Detail-page replay's `_last_event_at` stash via `getattr`.** §3.5 uses `getattr(run, "_last_event_at", None)` to read the field, defaulting to None if the replay loop didn't set it. If the replay loop forgets to set the field, the detail page falls back to running-forever behaviour for that one path. Mitigation: the replay-loop update is explicit in the spec and locked by a follow-on detail-replay test if added (deferred per §4).
- **Supabase `pushed_at` for older runs.** The four currently-stale rows have their original `pushed_at` (from the table default at INSERT time, days ago). After the deploy lands, their `pushed_at` is unchanged (no new push happens for a dead orchestrator). So `last_event_at = pushed_at` reads as "days ago" → staleness check fires → `abandoned`. Behaviour as expected. ✓
- **CHANGELOG / DS-SPEC.md prose drift.** A new lifecycle status that isn't reflected in the design-system vocabulary catalogue is a documentation gap. §3.7 lands the SPEC.md sub-section in the same PR.
- **Verification checklist from the Notion bug.** Five steps (audit DB, run API, spin up a fresh local run + kill, refresh list, confirm detail-page agreement). The implementer must execute all five before flipping the spec to `merged`. The third step (spin up local + kill mid-Phase 2) is the most load-bearing — it directly exercises the new branch end-to-end. Embed the verification screenshots / log excerpts in the PR description.
