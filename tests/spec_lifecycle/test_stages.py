"""Tests for scripts.spec_lifecycle.stages.compute_stages (post spec 0213).

Spec 0213 collapsed the 11 single-event rows into 7 honest spans (one
``(start_event, end_event)`` pair each). These tests lock the new shape:
seven canonical stages, span-based duration arithmetic, and the legacy
fallback that keeps historical specs (missing ``start_event``) showing
non-zero durations via the prior-row chain.
"""

from __future__ import annotations

import datetime as dt

from scripts.spec_lifecycle.stages import (
    STAGES,
    compute_stages,
    current_stage_label,
)


def _ev(step: str, ts: str = "2026-05-22T10:00:00Z", **data) -> dict:
    return {"ts": ts, "step": step, "data": data or {}}


def test_seven_canonical_stages() -> None:
    """The canonical stage list — 7 spans after spec 0213."""
    assert len(STAGES) == 7
    assert [s.name for s in STAGES] == [
        "Pre-flight",
        "Read & plan",
        "Implement",
        "Test",
        "Ship",
        "Deploy",
        "Handoff",
    ]
    # The (start_event, end_event) pairs — locked at the value level so any
    # accidental rewrite of the table shows up as a test diff.
    pairs = [(s.start_event, s.end_event) for s in STAGES]
    assert pairs == [
        ("cycle_started", "preflight_ok"),
        ("handoff_read", "reconcile_complete"),
        ("branched", "implement_complete"),
        ("tests_started", "tests_green"),
        ("pr_opened", "merged"),
        ("merged", "deployed"),
        ("deployed", "handoff_written"),
    ]


def test_empty_events_all_queued() -> None:
    """No events at all → stage 0 is current, the rest queued."""
    states, unknown = compute_stages("9999", [])
    assert unknown == []
    assert states[0].status == "curr"
    for s in states[1:]:
        assert s.status == "queued"


def test_partial_progress_current_stage_is_implement() -> None:
    """Cycle through Pre-flight + Read&plan; Implement is the current row."""
    events = [
        _ev("cycle_started", "2026-05-22T09:00:00Z"),
        _ev("queued", "2026-05-22T09:00:00Z"),
        _ev("in_progress", "2026-05-22T09:01:00Z"),
        _ev("preflight_ok", "2026-05-22T09:01:30Z"),
        _ev("handoff_read", "2026-05-22T09:02:00Z"),
        _ev("spec_read", "2026-05-22T09:03:00Z"),
        _ev("reconcile_complete", "2026-05-22T09:05:00Z", mechanical=2),
        _ev("branched", "2026-05-22T09:05:10Z", branch="spec/0213-x"),
    ]
    states, unknown = compute_stages("0213", events)
    assert unknown == []
    statuses = [s.status for s in states]
    # Pre-flight (0) + Read & plan (1) are done; Implement (2) is current.
    assert statuses[:2] == ["done", "done"]
    assert statuses[2] == "curr"
    assert all(s == "queued" for s in statuses[3:])


def test_all_seven_done() -> None:
    """When every span has its end_event, every stage is ``done`` and there's no current."""
    events = [
        _ev("cycle_started",      "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",       "2026-05-22T09:00:30Z"),
        _ev("handoff_read",       "2026-05-22T09:00:45Z"),
        _ev("spec_read",          "2026-05-22T09:01:00Z"),
        _ev("reconcile_complete", "2026-05-22T09:05:00Z"),
        _ev("branched",           "2026-05-22T09:05:10Z"),
        _ev("implement_complete", "2026-05-22T09:30:00Z"),
        _ev("tests_started",      "2026-05-22T09:30:30Z"),
        _ev("tests_green",        "2026-05-22T09:31:00Z"),
        _ev("pr_opened",          "2026-05-22T09:32:00Z"),
        _ev("merged",             "2026-05-22T09:33:00Z"),
        _ev("deployed",           "2026-05-22T09:40:00Z"),
        _ev("handoff_written",    "2026-05-22T09:41:00Z"),
    ]
    states, _ = compute_stages("0213", events)
    assert all(s.status == "done" for s in states)
    assert current_stage_label(states) is None


def test_failure_step_marks_correct_stage() -> None:
    """``failure_step: tests`` marks Test as fail; later stages stay queued."""
    events = [
        _ev("cycle_started",      "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",       "2026-05-22T09:00:01Z"),
        _ev("handoff_read",       "2026-05-22T09:00:02Z"),
        _ev("reconcile_complete", "2026-05-22T09:00:10Z"),
        _ev("branched",           "2026-05-22T09:00:12Z"),
        _ev("implement_complete", "2026-05-22T09:30:00Z"),
    ]
    states, _ = compute_stages("0213", events, failure_step="tests")
    statuses = [s.status for s in states]
    # 0 Pre-flight, 1 Read & plan, 2 Implement → all done; 3 Test → fail.
    assert statuses[:3] == ["done"] * 3
    assert statuses[3] == "fail"
    assert all(s == "queued" for s in statuses[4:])


def test_failure_step_aliases() -> None:
    """Aliases like 'pre-flight', 'deploy', 'reconcile', 'branch' resolve to the right stage."""
    for alias, expected_idx in [
        ("pre-flight", 0),
        ("preflight", 0),
        ("reconcile", 1),       # Read & plan
        ("read_handoff", 1),    # legacy alias maps into Read & plan
        ("read_spec", 1),
        ("branch", 2),          # Implement
        ("implement", 2),
        ("tests", 3),
        ("Test", 3),
        ("pr", 4),              # Ship
        ("merge", 4),
        ("deploy", 5),
        ("handoff", 6),
    ]:
        states, _ = compute_stages("9999", [_ev("in_progress")], failure_step=alias)
        statuses = [s.status for s in states]
        assert statuses[expected_idx] == "fail", f"alias {alias!r} did not mark stage {expected_idx}"


def test_unknown_events_surfaced() -> None:
    """Unknown step names are returned in the second tuple element so the renderer can warn."""
    events = [_ev("in_progress"), _ev("frobnicate"), _ev("xyzzy")]
    _, unknown = compute_stages("9999", events)
    assert "frobnicate" in unknown
    assert "xyzzy" in unknown


def test_current_stage_live_duration() -> None:
    """If ``now`` is provided, the current stage gets elapsed-time duration."""
    events = [
        _ev("cycle_started", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",  "2026-05-22T09:00:30Z"),
        _ev("handoff_read",  "2026-05-22T09:01:00Z"),
        _ev("reconcile_complete", "2026-05-22T09:02:00Z"),
        _ev("branched",      "2026-05-22T09:02:30Z"),
    ]
    now = dt.datetime(2026, 5, 22, 9, 30, 0, tzinfo=dt.timezone.utc)
    states, _ = compute_stages("9999", events, now=now)
    implement = states[2]
    assert implement.status == "curr"
    # 27m30s between branched (9:02:30) and now (9:30:00) = 1650 seconds
    assert implement.duration_seconds == 1650


def test_pre_flight_span_duration() -> None:
    """Pre-flight's span is ``cycle_started → preflight_ok``."""
    events = [
        _ev("cycle_started", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",  "2026-05-22T09:00:30Z"),
    ]
    states, _ = compute_stages("9999", events)
    # Pre-flight ran for 30s.
    assert states[0].duration_seconds == 30
    assert states[0].status == "done"


def test_read_and_plan_span_uses_handoff_read_as_start() -> None:
    """Read & plan spans `handoff_read → reconcile_complete` — does NOT
    absorb the gap between preflight_ok and handoff_read."""
    events = [
        _ev("cycle_started",      "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",       "2026-05-22T09:00:30Z"),
        # Buffered batch arrives all at 09:05 (the branch push in
        # /dev-next step 13). Read & plan should measure from handoff_read,
        # not from preflight_ok.
        _ev("handoff_read",       "2026-05-22T09:05:00Z"),
        _ev("spec_read",          "2026-05-22T09:05:01Z"),
        _ev("reconcile_complete", "2026-05-22T09:05:02Z", verdict="clean"),
    ]
    states, _ = compute_stages("9999", events)
    # Pre-flight: 30s.
    assert states[0].duration_seconds == 30
    # Read & plan: 2s (handoff_read → reconcile_complete), NOT 4m32s
    # (preflight_ok → reconcile_complete). The buffered emission shouldn't
    # poison the row's duration.
    assert states[1].duration_seconds == 2


def test_anchor_fallback_to_queued_for_legacy_specs() -> None:
    """Legacy specs without `cycle_started` fall back to `queued` (not `in_progress`)."""
    events = [
        _ev("queued", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:30Z"),
        _ev("in_progress", "2026-05-22T09:05:00Z"),
    ]
    states, _ = compute_stages("9999", events)
    # Pre-flight uses cycle_anchor (queued) since cycle_started is absent.
    assert states[0].duration_seconds == 30


def test_legacy_spec_without_start_events_uses_prior_end_fallback() -> None:
    """Historical specs that pre-date spec 0213 may lack `handoff_read` or
    `branched` start anchors. Fall back to the prior row's end_event so
    spec pages don't render all rows as zero."""
    events = [
        # No cycle_started, no handoff_read, no branched — the pre-0213
        # event vocab that older shipped specs carry.
        _ev("queued",             "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",       "2026-05-22T09:00:30Z"),
        _ev("reconcile_complete", "2026-05-22T09:05:00Z"),
        _ev("implement_complete", "2026-05-22T09:35:00Z"),
        _ev("tests_green",        "2026-05-22T09:36:00Z"),
    ]
    states, _ = compute_stages("9999", events)
    # Pre-flight uses cycle anchor (queued): 30s.
    assert states[0].duration_seconds == 30
    # Read & plan: no handoff_read, falls back to prior end (preflight_ok)
    # so duration is preflight_ok → reconcile_complete = 4m30s = 270s.
    assert states[1].duration_seconds == 270
    # Implement: no branched, falls back to prior end (reconcile_complete)
    # → implement_complete = 30m = 1800s.
    assert states[2].duration_seconds == 1800
    # Test: tests_started missing; fallback to implement_complete →
    # tests_green = 1m = 60s.
    assert states[3].duration_seconds == 60


def test_stage_started_at_exposed_on_state() -> None:
    """Each StageState carries `started_at` so the renderer can emit data attributes
    powering the dashboard live ticker (spec 0156 §2.3)."""
    events = [
        _ev("cycle_started", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",  "2026-05-22T09:00:10Z"),
        _ev("handoff_read",  "2026-05-22T09:00:20Z"),
        _ev("reconcile_complete", "2026-05-22T09:00:30Z"),
    ]
    states, _ = compute_stages("9999", events)
    # Stage 0 (Pre-flight) started at the cycle anchor.
    assert states[0].started_at is not None
    assert states[0].started_at.isoformat().startswith("2026-05-22T09:00:00")
    # Stage 1 (Read & plan) started at handoff_read.
    assert states[1].started_at is not None
    assert states[1].started_at.isoformat().startswith("2026-05-22T09:00:20")


def test_done_stage_duration_uses_span() -> None:
    """Done stages get the elapsed time of the span (end − start), not
    the cumulative chain delta."""
    events = [
        _ev("cycle_started",      "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",       "2026-05-22T09:00:05Z"),
        # Big gap before the buffered batch flushes:
        _ev("handoff_read",       "2026-05-22T09:01:00Z"),
        _ev("reconcile_complete", "2026-05-22T09:01:07Z"),
    ]
    states, _ = compute_stages("9999", events)
    # Pre-flight: cycle_started → preflight_ok = 5s.
    assert states[0].duration_seconds == 5
    # Read & plan: handoff_read → reconcile_complete = 7s
    # (NOT preflight_ok → reconcile_complete = 62s).
    assert states[1].duration_seconds == 7


def test_deploy_and_handoff_rows_tick_together_per_buffer_doctrine() -> None:
    """Spec 0212 doctrine: the post-merge events flush atomically at step 23.
    Deploy and Handoff rows render done in the same refresh — this is correct.

    Asserts the two rows compute sane durations even when their end_events
    share a timestamp (which they often do when the atomic push lands).
    """
    events = [
        _ev("cycle_started",      "2026-05-22T09:00:00Z"),
        _ev("preflight_ok",       "2026-05-22T09:00:30Z"),
        _ev("handoff_read",       "2026-05-22T09:05:00Z"),
        _ev("reconcile_complete", "2026-05-22T09:05:01Z"),
        _ev("branched",           "2026-05-22T09:05:10Z"),
        _ev("implement_complete", "2026-05-22T09:35:00Z"),
        _ev("tests_started",      "2026-05-22T09:35:30Z"),
        _ev("tests_green",        "2026-05-22T09:36:00Z"),
        _ev("pr_opened",          "2026-05-22T09:37:00Z"),
        _ev("merged",             "2026-05-22T09:38:00Z"),
        # Deploy + handoff fire in the same atomic flush at /dev-next step 23:
        _ev("deployed",           "2026-05-22T09:45:00Z"),
        _ev("handoff_written",    "2026-05-22T09:45:00Z"),
    ]
    states, _ = compute_stages("9999", events)
    deploy = states[5]
    handoff = states[6]
    assert deploy.status == "done"
    assert handoff.status == "done"
    # Deploy = merged → deployed = 7m = 420s.
    assert deploy.duration_seconds == 420
    # Handoff = deployed → handoff_written = 0s (atomic flush).
    assert handoff.duration_seconds == 0
