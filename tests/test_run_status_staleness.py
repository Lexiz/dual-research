"""Spec 0181 — staleness branch in derive_run_status + call-site plumbing.

The truth table now classifies silent runs as `abandoned`. This test
locks the branch with pinned-now determinism and asserts all three call
sites pass `last_event_at` through to the truth table.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    # Edge: state_phase == "done" triggers the completed branch BEFORE the
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


def test_iso_z_suffix_parses_correctly():
    # Wire format uses `Z` suffix for UTC; ensure derive_run_status handles it.
    status = derive_run_status(
        state_phase="phase2",
        final_emitted=False,
        hard_cap_hit=False,
        run_failed=False,
        run_completed_exit_code=None,
        last_event_at="2026-01-01T00:00:00Z",  # very old, Z suffix
        now=NOW,
    )
    assert status == "abandoned"


def test_garbage_last_event_at_falls_through_to_running():
    # A malformed timestamp must not crash; it falls through to running.
    status = derive_run_status(
        state_phase="phase2",
        final_emitted=False,
        hard_cap_hit=False,
        run_failed=False,
        run_completed_exit_code=None,
        last_event_at="not-a-timestamp",
        now=NOW,
    )
    assert status == "running"


# ─── Call-site plumbing ───────────────────────────────────────────────────


def test_summarize_run_passes_last_event_at(tmp_path: Path):
    """`summarize_run` must read the last event ts from the transcript
    and pass it through to `derive_run_status`."""
    from dual_research.ui import aggregator

    session_dir = tmp_path / "20260101-000000-test-stale"
    session_dir.mkdir()
    # Write a transcript with a single old event — no terminal signals.
    transcript = session_dir / "transcript.jsonl"
    transcript.write_text(
        '{"seq": 1, "ts": "2026-01-01T00:00:00+00:00", "event": "phase_entered", '
        '"phase": "phase2"}\n'
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


def test_status_from_columns_no_last_event_at_is_running():
    """Backwards compat — when callers omit last_event_at, behaviour matches
    pre-spec-0181 (returns running, no abandoned classification)."""
    from dual_research.ui.server import _status_from_columns

    status = _status_from_columns(
        phase_reached="phase2",
        exit_code=None,
        state={},
    )
    assert status == "running"


# ─── Spec 0195 — _earliest_known_ts + summarize_run fallback ─────────────


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

    Frontend renders this as "—" rather than "0s ago" via the spec 0195
    cell-level guard in run-list.jsx.
    """
    from dual_research.ui import aggregator

    session_dir = tmp_path / "weird-name-no-ts-prefix"
    session_dir.mkdir()
    (session_dir / "state.json").write_text('{"phase": "phase2"}')

    row = aggregator.summarize_run(session_dir)
    assert row.started_at is None
    assert row.started_at_ago == 0


def test_summarize_run_prefers_transcript_first_event_over_dir_ts(tmp_path: Path):
    """When transcript.jsonl has events, the first event's ts wins over the
    dir-name prefix — the dir prefix is a strict fallback, not a primary."""
    from dual_research.ui import aggregator

    session_dir = tmp_path / "20260101-120000-with-events"
    session_dir.mkdir()
    (session_dir / "transcript.jsonl").write_text(
        '{"ts": "2026-06-15T08:30:00+00:00", "type": "run_started"}\n'
    )

    row = aggregator.summarize_run(session_dir)
    # First-event ts wins; not the dir-name prefix.
    assert row.started_at is not None
    assert row.started_at.startswith("2026-06-15T08:30:00")


def test_earliest_known_ts_returns_dir_prefix_when_transcript_empty(tmp_path: Path):
    """Unit-level check on the helper itself — empty transcript file (file
    exists but no parseable lines) still falls back to the dir prefix."""
    from dual_research.ui.aggregator import _earliest_known_ts

    session_dir = tmp_path / "20260315-093015-empty-transcript"
    session_dir.mkdir()
    (session_dir / "transcript.jsonl").write_text("")  # exists, but empty

    ts = _earliest_known_ts(session_dir)
    assert ts is not None
    assert ts.startswith("2026-03-15T09:30:15")
