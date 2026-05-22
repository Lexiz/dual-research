"""Tests for scripts.spec_lifecycle.stages.compute_stages."""

from __future__ import annotations

import datetime as dt

from scripts.spec_lifecycle.stages import (
    STAGES,
    compute_stages,
    current_stage_label,
)


def _ev(step: str, ts: str = "2026-05-22T10:00:00Z", **data) -> dict:
    return {"ts": ts, "step": step, "data": data or {}}


def test_eleven_canonical_stages() -> None:
    """The canonical stage list must match the /dev-next cycle (spec 0152 §2.7)."""
    assert len(STAGES) == 11
    assert [s.name for s in STAGES] == [
        "Pre-flight",
        "Read handoff",
        "Read spec",
        "Reconcile",
        "Branch",
        "Implement",
        "Test",
        "PR",
        "Merge",
        "Deploy",
        "Handoff",
    ]


def test_empty_events_all_queued() -> None:
    """No events at all → stage 0 is current, the rest queued."""
    states, unknown = compute_stages("9999", [])
    assert unknown == []
    assert states[0].status == "curr"
    for s in states[1:]:
        assert s.status == "queued"


def test_partial_progress_current_stage() -> None:
    """Walk through done stages and stop at the current."""
    events = [
        _ev("queued", "2026-05-22T09:00:00Z"),
        _ev("in_progress", "2026-05-22T09:01:00Z"),
        _ev("preflight_ok", "2026-05-22T09:01:30Z"),
        _ev("handoff_read", "2026-05-22T09:02:00Z"),
        _ev("spec_read", "2026-05-22T09:03:00Z"),
        _ev("reconcile_complete", "2026-05-22T09:05:00Z", mechanical=2),
        _ev("branched", "2026-05-22T09:05:10Z", branch="spec/0153-x"),
    ]
    states, unknown = compute_stages("0153", events)
    assert unknown == []
    statuses = [s.status for s in states]
    assert statuses[:5] == ["done", "done", "done", "done", "done"]
    assert statuses[5] == "curr"
    assert all(s == "queued" for s in statuses[6:])


def test_all_eleven_done() -> None:
    """When all eleven event steps fired, every stage is ``done`` and there's no current."""
    events = [
        _ev("in_progress", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:01Z"),
        _ev("handoff_read", "2026-05-22T09:00:02Z"),
        _ev("spec_read", "2026-05-22T09:00:03Z"),
        _ev("reconcile_complete", "2026-05-22T09:00:10Z"),
        _ev("branched", "2026-05-22T09:00:12Z"),
        _ev("implement_complete", "2026-05-22T09:30:00Z"),
        _ev("tests_green", "2026-05-22T09:31:00Z"),
        _ev("pr_opened", "2026-05-22T09:32:00Z"),
        _ev("merged", "2026-05-22T09:33:00Z"),
        _ev("deployed", "2026-05-22T09:40:00Z"),
        _ev("handoff_written", "2026-05-22T09:41:00Z"),
    ]
    states, _ = compute_stages("0153", events)
    assert all(s.status == "done" for s in states)
    assert current_stage_label(states) is None


def test_failure_step_marks_correct_stage() -> None:
    """``failure_step: tests`` marks Test as fail; later stages stay queued."""
    events = [
        _ev("in_progress", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:01Z"),
        _ev("handoff_read", "2026-05-22T09:00:02Z"),
        _ev("spec_read", "2026-05-22T09:00:03Z"),
        _ev("reconcile_complete", "2026-05-22T09:00:10Z"),
        _ev("branched", "2026-05-22T09:00:12Z"),
        _ev("implement_complete", "2026-05-22T09:30:00Z"),
    ]
    states, _ = compute_stages("0153", events, failure_step="tests")
    statuses = [s.status for s in states]
    assert statuses[:6] == ["done"] * 6
    assert statuses[6] == "fail"
    assert all(s == "queued" for s in statuses[7:])


def test_failure_step_aliases() -> None:
    """Aliases like 'pre-flight', 'deploy' resolve to the right stage."""
    for alias, expected_idx in [
        ("pre-flight", 0),
        ("preflight", 0),
        ("reconcile", 3),
        ("deploy", 9),
        ("Test", 6),
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
        _ev("in_progress", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:30Z"),
        _ev("handoff_read", "2026-05-22T09:01:00Z"),
        _ev("spec_read", "2026-05-22T09:01:30Z"),
        _ev("reconcile_complete", "2026-05-22T09:02:00Z"),
        _ev("branched", "2026-05-22T09:02:30Z"),
    ]
    now = dt.datetime(2026, 5, 22, 9, 30, 0, tzinfo=dt.timezone.utc)
    states, _ = compute_stages("9999", events, now=now)
    implement = states[5]
    assert implement.status == "curr"
    # 30 minutes between branched (9:02:30) and now (9:30:00) = 1650 seconds
    assert implement.duration_seconds == 1650


def test_cycle_started_anchor_gives_real_preflight_duration() -> None:
    """Spec 0156: `cycle_started` is the cycle anchor so pre-flight gets real timing.

    Before the fix the anchor was `in_progress`, which /dev-next emits in step 12
    *alongside* the buffered early events. That made `preflight_ok_ts - in_progress_ts`
    negative, clipped to 0 by ``max(0, ...)``, and Pre-flight / Read handoff /
    Read spec all showed 0s on the dashboard regardless of real duration.
    """
    events = [
        _ev("cycle_started", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:30Z"),
        _ev("handoff_read", "2026-05-22T09:00:45Z"),
        _ev("spec_read", "2026-05-22T09:01:00Z"),
        # in_progress arrives later (it's the step-12 emission), and would have
        # poisoned the anchor before this fix.
        _ev("in_progress", "2026-05-22T09:05:00Z"),
    ]
    states, unknown = compute_stages("9999", events)
    assert unknown == []
    # Pre-flight ran for 30s (cycle_started → preflight_ok).
    assert states[0].duration_seconds == 30
    # Subsequent done stages get the right deltas.
    assert states[1].duration_seconds == 15  # preflight_ok → handoff_read
    assert states[2].duration_seconds == 15  # handoff_read → spec_read


def test_anchor_fallback_to_queued_for_legacy_specs() -> None:
    """Legacy specs without `cycle_started` fall back to `queued` (not `in_progress`).

    Conflates queue-dwell time with pre-flight, but is non-zero and broadly
    correct for historical specs — better than the prior anchor that clipped
    durations to 0.
    """
    events = [
        _ev("queued", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:30Z"),
        _ev("in_progress", "2026-05-22T09:05:00Z"),
    ]
    states, _ = compute_stages("9999", events)
    assert states[0].duration_seconds == 30
    # And anchor falls back to in_progress only if neither cycle_started nor queued exist.
    events_only_inprogress = [
        _ev("in_progress", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:30Z"),
    ]
    states_b, _ = compute_stages("9999", events_only_inprogress)
    assert states_b[0].duration_seconds == 30


def test_stage_started_at_exposed_on_state() -> None:
    """Each StageState carries `started_at` so the renderer can emit data attributes
    powering the dashboard live ticker (spec 0156 §2.3)."""
    events = [
        _ev("cycle_started", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:10Z"),
        _ev("handoff_read", "2026-05-22T09:00:20Z"),
    ]
    states, _ = compute_stages("9999", events)
    # Stage 0 (Pre-flight) started at the cycle anchor.
    assert states[0].started_at is not None
    assert states[0].started_at.isoformat().startswith("2026-05-22T09:00:00")
    # Stage 1 (Read handoff) started when preflight_ok fired.
    assert states[1].started_at is not None
    assert states[1].started_at.isoformat().startswith("2026-05-22T09:00:10")


def test_done_stage_duration() -> None:
    """Done stages get the elapsed time between their event and the prior event."""
    events = [
        _ev("in_progress", "2026-05-22T09:00:00Z"),
        _ev("preflight_ok", "2026-05-22T09:00:05Z"),
        _ev("handoff_read", "2026-05-22T09:00:07Z"),
    ]
    states, _ = compute_stages("9999", events)
    assert states[0].duration_seconds == 5
    assert states[1].duration_seconds == 2
