"""Spec 0163 — the five new informational step names don't trip stage logic."""

from __future__ import annotations

import datetime as dt

from scripts.spec_lifecycle.stages import (
    STEP_LABELS,
    TOLERATED_NON_STAGE_STEPS,
    compute_stages,
)


NEW_STEPS = (
    "planning_started",
    "implementing_started",
    "tests_started",
    "deploy_started",
    "deploy_health_check_ok",
)


def test_new_steps_are_tolerated() -> None:
    for step in NEW_STEPS:
        assert step in TOLERATED_NON_STAGE_STEPS, step


def test_compute_stages_does_not_flag_new_steps_as_unknown() -> None:
    now = dt.datetime(2026, 5, 22, 12, 0, 0, tzinfo=dt.timezone.utc)
    events = [
        {"ts": "2026-05-22T10:00:00Z", "step": "cycle_started", "data": {}},
        {"ts": "2026-05-22T10:00:30Z", "step": "preflight_ok", "data": {}},
        {"ts": "2026-05-22T10:01:00Z", "step": "handoff_read", "data": {}},
        {"ts": "2026-05-22T10:01:30Z", "step": "spec_read", "data": {}},
        {"ts": "2026-05-22T10:01:35Z", "step": "planning_started", "data": {}},
        {"ts": "2026-05-22T10:02:00Z", "step": "reconcile_complete", "data": {}},
        {"ts": "2026-05-22T10:02:30Z", "step": "in_progress", "data": {}},
        {"ts": "2026-05-22T10:03:00Z", "step": "branched", "data": {}},
        {"ts": "2026-05-22T10:03:05Z", "step": "implementing_started", "data": {}},
        {"ts": "2026-05-22T10:30:00Z", "step": "implement_complete", "data": {}},
        {"ts": "2026-05-22T10:30:30Z", "step": "tests_started", "data": {}},
        {"ts": "2026-05-22T10:31:00Z", "step": "tests_green", "data": {}},
        {"ts": "2026-05-22T10:31:30Z", "step": "pr_opened", "data": {}},
        {"ts": "2026-05-22T10:32:00Z", "step": "merged", "data": {}},
        {"ts": "2026-05-22T10:33:00Z", "step": "deploy_started", "data": {}},
        {"ts": "2026-05-22T10:35:00Z", "step": "deployed", "data": {}},
        {"ts": "2026-05-22T10:35:30Z", "step": "deploy_health_check_ok", "data": {}},
        {"ts": "2026-05-22T10:36:00Z", "step": "handoff_written", "data": {}},
    ]
    _states, unknown = compute_stages("0163", events, now=now)
    assert unknown == [], f"unexpected unknown steps: {unknown}"


def test_step_labels_cover_every_emitted_step() -> None:
    """Every step the orchestrator emits has a friendly label."""
    expected = {
        "queued", "cycle_started", "preflight_ok", "handoff_read", "spec_read",
        "planning_started", "reconcile_complete", "in_progress", "branched",
        "implementing_started", "implement_complete", "tests_started",
        "tests_green", "pr_opened", "merged", "deploy_started", "deployed",
        "deploy_health_check_ok", "handoff_written",
    }
    missing = expected - STEP_LABELS.keys()
    assert not missing, f"STEP_LABELS missing labels for: {missing}"
