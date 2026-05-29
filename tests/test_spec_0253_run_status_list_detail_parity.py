"""Spec 0253 — All-Runs card status must match the run-detail status.

The bug: the list paths fed ``derive_run_status`` a *different*
``last_event_at`` input than the detail path. The supabase list used the
``pushed_at`` row-upsert ts (a bulk re-upsert reset it to ~now,
resurrecting dead runs to ``running``); the filesystem list used a file
mtime fallback and returned ``None`` on a truncated final transcript
line. The detail path replays the real events and so read ``abandoned``.
Same truth table, two inputs, two answers.

These tests exercise the *real* list entry points (``_supabase_list_runs``
/ ``summarize_run``) against captured-shape artifacts and assert parity
with the detail path (``_materialize_snapshot_supabase`` /
``load_run_snapshot``) — spec 0238 live-failure discipline + spec 0206's
pure-stdlib, no-Playwright doctrine.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dual_research.ui.aggregator import (
    _latest_event_ts,
    load_run_snapshot,
    summarize_run,
)
from dual_research.ui.server import (
    _materialize_snapshot_supabase,
    _max_event_ts_by_run,
    _supabase_list_runs,
)

from .ui.supabase_fake import FakeSupabaseClient

# Well past RUN_STALE_THRESHOLD_MINUTES relative to any plausible test "now".
OLD = "2026-01-01T00:00:00+00:00"
OLD2 = "2026-01-01T00:05:00+00:00"


def _recent(minutes_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _list_status(fake: FakeSupabaseClient, run_id: str) -> str:
    rows = _supabase_list_runs(fake)
    row = next(r for r in rows if r.id == run_id)
    return row.status


def _detail_status(fake: FakeSupabaseClient, run_id: str) -> str:
    return _materialize_snapshot_supabase(fake, run_id)["status"]


# ─── Supabase parity (the real bug) ───────────────────────────────────────


def test_supabase_stale_run_list_matches_detail_abandoned() -> None:
    """The captured misfire: events all > 30 min old, but a recent
    ``pushed_at`` (bumped by a bulk re-upsert) and a null exit_code. The
    list must read the SAME ``abandoned`` the detail page replays — not
    ``running`` off the stale ``pushed_at`` proxy."""
    run_id = "20260524-135902-spec0253-stale"
    fake = FakeSupabaseClient()
    recent_push = _recent(16)
    fake.runs.append(
        {
            "id": run_id,
            "slug": "stale",
            "created_at": OLD,
            "phase_reached": "phase2",
            "exit_code": None,  # no terminal signal
            "duration_ms": None,
            "total_cost_usd": 0.1,
            "state": {"phase": "phase2"},
            "metrics": None,
            # The trigger: recent, NOT null — reproduces the bulk re-push.
            "pushed_at": recent_push,
            "deleted_at": None,
            "deleted_by": None,
        }
    )
    fake.session_files.extend(
        [
            {"run_id": run_id, "path": "brief.md", "content": "# Stale run\n"},
            {"run_id": run_id, "path": "state.json", "content": json.dumps({"phase": "phase2"})},
        ]
    )
    fake.events.extend(
        [
            {"run_id": run_id, "seq": 0, "ts": OLD, "kind": "phase_entered", "payload": {"phase": "phase2"}},
            {"run_id": run_id, "seq": 1, "ts": OLD2, "kind": "turn_started", "payload": {}},
        ]
    )

    # Fixture fidelity (spec 0253 §8): the trigger is a recent pushed_at,
    # not a null one. Lock it so the test reproduces the actual misfire.
    assert _recent(20) < recent_push, "pushed_at must be recent to reproduce the bug"

    assert _list_status(fake, run_id) == "abandoned"
    assert _detail_status(fake, run_id) == "abandoned"


def test_supabase_no_events_old_row_list_reads_abandoned() -> None:
    """Zero events + old created_at + recent pushed_at → the list falls
    back to ``created_at`` and reads ``abandoned``, not ``running`` off
    ``pushed_at`` (spec 0253 §3.1 fallback)."""
    run_id = "20260101-000000-spec0253-noevents"
    fake = FakeSupabaseClient()
    fake.runs.append(
        {
            "id": run_id,
            "slug": "noevents",
            "created_at": OLD,
            "phase_reached": "phase2",
            "exit_code": None,
            "duration_ms": None,
            "total_cost_usd": 0.0,
            "state": {"phase": "phase2"},
            "metrics": None,
            "pushed_at": _recent(16),
            "deleted_at": None,
            "deleted_by": None,
        }
    )
    fake.session_files.append({"run_id": run_id, "path": "brief.md", "content": "# No events\n"})
    # No events seeded.

    assert _list_status(fake, run_id) == "abandoned"


def test_supabase_healthy_run_list_matches_detail_running() -> None:
    """A run whose last event is recent and which has no terminal signal
    still reads ``running`` on BOTH surfaces — no false-abandoned."""
    run_id = "20260529-120000-spec0253-healthy"
    fake = FakeSupabaseClient()
    fake.runs.append(
        {
            "id": run_id,
            "slug": "healthy",
            "created_at": _recent(20),
            "phase_reached": "phase2",
            "exit_code": None,
            "duration_ms": None,
            "total_cost_usd": 0.1,
            "state": {"phase": "phase2"},
            "metrics": None,
            "pushed_at": _recent(2),
            "deleted_at": None,
            "deleted_by": None,
        }
    )
    fake.session_files.extend(
        [
            {"run_id": run_id, "path": "brief.md", "content": "# Healthy run\n"},
            {"run_id": run_id, "path": "state.json", "content": json.dumps({"phase": "phase2"})},
        ]
    )
    fake.events.append(
        {"run_id": run_id, "seq": 0, "ts": _recent(5), "kind": "phase_entered", "payload": {"phase": "phase2"}}
    )

    assert _list_status(fake, run_id) == "running"
    assert _detail_status(fake, run_id) == "running"


# ─── _max_event_ts_by_run unit coverage ───────────────────────────────────


def test_max_event_ts_by_run_picks_per_run_max() -> None:
    fake = FakeSupabaseClient()
    fake.events.extend(
        [
            {"run_id": "A", "seq": 0, "ts": OLD, "kind": "x", "payload": {}},
            {"run_id": "A", "seq": 1, "ts": OLD2, "kind": "x", "payload": {}},
            {"run_id": "B", "seq": 0, "ts": "2026-03-03T03:03:03+00:00", "kind": "x", "payload": {}},
        ]
    )
    out = _max_event_ts_by_run(fake, ["A", "B"])
    assert out == {"A": OLD2, "B": "2026-03-03T03:03:03+00:00"}


def test_max_event_ts_by_run_paginates_past_page_size() -> None:
    fake = FakeSupabaseClient()
    # 1001 rows for one run crosses the 1000-row page boundary; the max ts
    # must survive the pagination loop. Distinct, sortable ISO timestamps.
    for i in range(1001):
        fake.events.append(
            {"run_id": "P", "seq": i, "ts": f"2026-02-01T00:{i // 60:02d}:{i % 60:02d}+00:00", "kind": "x", "payload": {}}
        )
    out = _max_event_ts_by_run(fake, ["P"])
    assert out["P"] == "2026-02-01T00:16:40+00:00"  # i == 1000


def test_max_event_ts_by_run_empty_ids_returns_empty() -> None:
    assert _max_event_ts_by_run(FakeSupabaseClient(), []) == {}


# ─── Filesystem parity ─────────────────────────────────────────────────────


def test_fs_truncated_final_line_list_matches_detail_abandoned(tmp_path: Path) -> None:
    """The SIGKILL-mid-write signature: a corrupt final transcript line on
    top of older valid events. The list must walk back to the last valid
    event (old → abandoned) and match the detail replay — not return
    ``None`` and fall through to ``running`` (the pre-0253 bug)."""
    session_dir = tmp_path / "20260101-000000-fs-truncated"
    session_dir.mkdir()
    (session_dir / "transcript.jsonl").write_text(
        '{"seq": 0, "ts": "2026-01-01T00:00:00+00:00", "event": "phase_entered", "phase": "phase2"}\n'
        '{"seq": 1, "ts": "2026-01-01T00:05:00+00:00", "event": "turn_started"}\n'
        '{"seq": 2, "ts": "2026-01-0'  # truncated — no closing brace, no newline
    )
    (session_dir / "state.json").write_text(json.dumps({"phase": "phase2"}))

    assert summarize_run(session_dir).status == "abandoned"
    assert load_run_snapshot(session_dir).status == "abandoned"


def test_fs_all_corrupt_transcript_old_dir_reads_abandoned(tmp_path: Path) -> None:
    """No valid event anywhere + a recently-written state.json (recent
    mtime) + an old dir-name ts → the list reads ``abandoned`` off the
    creation time, NOT ``running`` off the mtime (spec 0253 dropped the
    mtime fallback)."""
    session_dir = tmp_path / "20260101-000000-fs-allcorrupt"
    session_dir.mkdir()
    (session_dir / "transcript.jsonl").write_text("{bad json\n@@@ not json @@@\n")
    # Written now → recent mtime. The pre-0253 code used this and read running.
    (session_dir / "state.json").write_text(json.dumps({"phase": "phase2"}))

    assert summarize_run(session_dir).status == "abandoned"


def test_fs_healthy_recent_event_list_matches_detail_running(tmp_path: Path) -> None:
    session_dir = tmp_path / "20260529-120000-fs-healthy"
    session_dir.mkdir()
    (session_dir / "transcript.jsonl").write_text(
        json.dumps({"seq": 0, "ts": _recent(5), "event": "phase_entered", "phase": "phase2"}) + "\n"
    )
    (session_dir / "state.json").write_text(json.dumps({"phase": "phase2"}))

    assert summarize_run(session_dir).status == "running"
    assert load_run_snapshot(session_dir).status == "running"


# ─── _latest_event_ts resilient walk-back ──────────────────────────────────


def test_latest_event_ts_walks_back_past_corrupt_tail(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        '{"seq": 0, "ts": "2026-01-01T00:00:00+00:00", "event": "a"}\n'
        '{"seq": 1, "ts": "2026-01-01T00:05:00+00:00", "event": "b"}\n'
        '{"seq": 2, "ts": "2026-01-0'  # truncated
    )
    # The last VALID event's ts, not None.
    assert _latest_event_ts(transcript) == "2026-01-01T00:05:00+00:00"


def test_latest_event_ts_none_when_no_valid_event(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{bad\n@@@\n")
    assert _latest_event_ts(transcript) is None


def test_latest_event_ts_missing_file_is_none(tmp_path: Path) -> None:
    assert _latest_event_ts(tmp_path / "nope.jsonl") is None
