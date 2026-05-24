"""Spec 0203.1 — event-vocab parity: the three new step names emitted by
the L-spec checkpoint cadence (`checkpoint_written`, `resume_started`) and
the `/spec-next` skill (`promoted_as_next`) must not trip the dashboard's
"unknown event step" warning and must carry friendly labels.
"""

from __future__ import annotations

import datetime as dt

from scripts.spec_lifecycle.stages import (
    STEP_LABELS,
    TOLERATED_NON_STAGE_STEPS,
    compute_stages,
)


NEW_STEPS = (
    "checkpoint_written",
    "resume_started",
    "promoted_as_next",
)


def test_new_steps_are_tolerated() -> None:
    for step in NEW_STEPS:
        assert step in TOLERATED_NON_STAGE_STEPS, step


def test_new_steps_have_step_labels() -> None:
    expected_labels = {
        "checkpoint_written": "checkpoint",
        "resume_started": "resuming",
        "promoted_as_next": "promoted as next",
    }
    for step, label in expected_labels.items():
        assert STEP_LABELS.get(step) == label, (step, STEP_LABELS.get(step))


def test_compute_stages_does_not_flag_new_steps_as_unknown() -> None:
    """Build an L-spec event stream that exercises all three new steps and
    confirm `compute_stages` returns an empty `unknown_events` list."""
    now = dt.datetime(2026, 5, 24, 12, 0, 0, tzinfo=dt.timezone.utc)
    events = [
        {"ts": "2026-05-24T10:00:00Z", "step": "queued", "data": {}},
        {"ts": "2026-05-24T10:00:05Z", "step": "promoted_as_next",
         "data": {"was": "0205", "cascade": 0}},
        {"ts": "2026-05-24T10:00:10Z", "step": "cycle_started", "data": {}},
        {"ts": "2026-05-24T10:00:30Z", "step": "preflight_ok", "data": {}},
        {"ts": "2026-05-24T10:00:35Z", "step": "in_progress", "data": {}},
        {"ts": "2026-05-24T10:01:00Z", "step": "branched", "data": {}},
        {"ts": "2026-05-24T10:01:05Z", "step": "implementing_started", "data": {}},
        {"ts": "2026-05-24T10:30:00Z", "step": "checkpoint_written",
         "data": {"next_subsection": "2.3", "completed_subsections": ["2.1", "2.2"]}},
        {"ts": "2026-05-24T11:00:00Z", "step": "resume_started",
         "data": {"from_checkpoint": "handoffs/x.md", "next_subsection": "2.3"}},
    ]
    _states, unknown = compute_stages("0203.1", events, now=now)
    assert unknown == [], f"unexpected unknown steps: {unknown}"
